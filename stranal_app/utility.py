import datetime

from cerberus import Validator as _Validator
from sqlalchemy import inspect
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.exc import NoInspectionAvailable


def is_sqla_obj(obj):
    """Checks if an object is a SQLAlchemy model instance."""
    try:
        inspect(obj)
        return True
    except NoInspectionAvailable:
        return False


def import_into_sqla_object(model_instance, data):
    """ Import a dictionary into a SQLAlchemy model instance. Only those
    keys in `data` that match a column name in the model instance are
    imported, everthing else is omitted.

    This function does not validate the values coming in `data`.

    :param model_instance: A SQLAlchemy model instance.
    :param data: A python dictionary.
    """

    mapper = inspect(model_instance.__class__)

    for key in data:
        if key in mapper.c:
            setattr(model_instance, key, data[key])

    return model_instance


def _get_column_default(c):
    d = c.default
    return d.arg if isinstance(getattr(d, "arg", None), (int, str, bool)) else None


class ExportData:
    """ Creates a callable object that convert SQLAlchemy model instances
    to dictionaries.
    """

    def __init__(self, exclude=()):

        #: A global list of column names to exclude. This takes precedence over
        #: the parameters ``include`` and/or ``exclude`` of this instance call.
        self.exclude = tuple(exclude)

    def __call__(self, obj, include=(), exclude=()):
        """Converts SQLAlchemy models into python serializable objects. It can
        take a single model or a list of models.

        By default, all columns are included in the output, unless a list of
        column names are provided to the parameters ``include`` or ``exclude``.
        The latter has precedence over the former. Finally, the columns that
        appear in the :attr:`excluded` property will be excluded, regardless of
        the values that the parameters include and exclude have.

        If the model is not persisted in the database, the default values of
        the columns are used if they exist in the class definition. From the
        example below, the value False will be used for the column active::

            active = Column(Boolean, default=False)

        :param obj: A instance or a list of SQLAlchemy model instances.
        :param include: tuple, list or set.
        :param exclude: tuple, list or set.
        """

        if isinstance(obj, (list, InstrumentedList)):
            try:
                return [item.export_data(include, exclude) for item in obj]
            except AttributeError as e:
                # If the method exist, the exception comes inside of it.
                if hasattr(obj[0], "export_data"):
                    # So re-raise the exception.
                    raise e

                return [self(item, include, exclude) for item in obj]

        try:
            persisted = inspect(obj).persistent
        except NoInspectionAvailable as e:
            raise ValueError("Pass a valid SQLAlchemy mapped class instance")

        columns = obj.__mapper__.columns
        exclude = tuple(exclude) + self.exclude
        data = {}

        for c in columns:
            name = c.name

            if (not include or name in include) and name not in exclude:
                column_value = getattr(obj, name)

                data[name] = (
                    column_value
                    if persisted
                    else _get_column_default(c)
                    if column_value is None
                    else column_value
                )

        if persisted is True:
            unloaded_relationships = inspect(obj).unloaded
            relationship_keys = [
                relationship.key
                for relationship in obj.__class__.__mapper__.relationships
            ]

            for key in relationship_keys:
                if key not in unloaded_relationships and key not in exclude:
                    rproperty = getattr(obj, key)
                    has_export_data = hasattr(rproperty, "export_data")
                    data[key] = None

                    if has_export_data:
                        data[key] = rproperty.export_data()
                    elif rproperty:
                        data[key] = self(rproperty)

        return data


#: Converts SQLAlchemy models into python serializable objects.
#:
#: This is an instance of :class:`ExportData` so head on to the
#: :meth:`~ExportData.__call__` method to known how this work. This instances
#: globally removes columns named ``org_id``.
export_from_sqla_object = ExportData(exclude=("org_id",))


schema_type_conversions = {
    int: "integer",
    str: "string",
    bool: "boolean",
    datetime.date: "string",
    datetime.datetime: "string",
}


def generate_schema(model_class, include=(), exclude=(), exclude_rules=None):
    """ Inspects a SQLAlchemy model class and returns a validation schema to be
    used with the Cerberus library. The schema is generated mapping column
    types and constraints to Cerberus rules:

    +---------------+------------------------------------------------------+
    | Cerberus Rule | Based on                                             |
    +===============+======================================================+
    | type          | SQLAlchemy column class used (String, Integer, etc). |
    +---------------+------------------------------------------------------+
    | readonly      | **True** if the column is primary key.               |
    +---------------+------------------------------------------------------+
    | required      | **True** if ``Column.nullable`` is **False** or      |
    |               | ``Column.default`` and ``Column.server_default``     |
    |               | **None**.                                            |
    +---------------+------------------------------------------------------+
    | unique        | Included only when the ``unique`` constraint is      |
    |               | ``True``, otherwise is omitted:                      |
    |               | ``Column(unique=True)``                              |
    +---------------+------------------------------------------------------+
    | default       | Not included in the output. This is handled by       |
    |               | SQLAlchemy or by the database engine.                |
    +---------------+------------------------------------------------------+

    :param model_class: SQLAlchemy model class.
    :param include: List of columns to include in the output.
    :param exclude: List of column to exclude from the output.
    :param exclude_rules: Rules to be excluded from the output.
    """

    schema = {}
    exclude_rules = exclude_rules or []

    mapper = inspect(model_class)

    for column in mapper.c:

        name = column.name

        if len(include) > 0 and name not in include:
            continue

        if name in exclude:
            continue

        prop = {}

        python_type = column.type.python_type

        prop["type"] = schema_type_conversions.get(python_type)

        if prop["type"] is None:
            raise LookupError("Unable to determine the column type")

        if (
            "readonly" not in exclude_rules
            and python_type == str
            and column.type.length is not None
        ):
            prop["maxlength"] = column.type.length

        if "readonly" not in exclude_rules and column.primary_key is True:
            prop["readonly"] = True

        if (
            "required" not in exclude_rules
            and column.default is None
            and column.server_default is None
            and column.nullable is False
            and column.primary_key is False
        ):
            prop["required"] = True

        if "unique" not in exclude_rules and column.unique:
            prop["unique"] = True

        schema[name] = prop

    return schema


class Validator(_Validator):
    def __init__(self, schema, model_class=None, **kwargs):
        super(Validator, self).__init__(schema, **kwargs)
        self.model_class = model_class

    def validate(self, document, model=None, **kwargs):

        self.model = model

        return super(Validator, self).validate(document, **kwargs)

    def _validate_unique(self, is_unique, field, value):
        """Performs a query to the database to check value is already present
        in a given column.

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """

        if is_unique:
            if not self.model_class:
                raise RuntimeError(
                    "The rule `unique` needs a SQLAlchemy declarative class"
                    " to perform queries to check if the value being validated"
                    " is unique. Provide a class in Validator constructor."
                )

            filters = {field: value}
            model = self.model_class.query.filter_by(**filters).first()

            if model and (not self.update or model is not self.model):
                self._error(field, f"Must be unique, but '{value}' already exist")


def get_key_path(key, _map):

    for map_key, value in _map.items():
        path = []

        if map_key == key:
            return [map_key]

        if type(value) == dict:
            _path = get_key_path(key, value)
            path = ([map_key] + path + _path) if _path else []

        if len(path) > 0:
            return path

    return None
