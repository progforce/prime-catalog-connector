# -*- coding: utf-8 -*-
##############################################################################
#
#    Prime Catalog Connector
#    Copyright (C) 2017 Progforce, LLC (<http://progforce.com/>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.tools import ustr
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from functools import wraps
from json import loads as json_loads
import logging

_logger = logging.getLogger(__name__)


def raise_bad_odoo_type(types):

    def decorator(function):

        @wraps(function)
        def wrapped(self, *args, **kwargs):
            if self.odoo_type not in types:
                raise NotImplementedError(
                    'bad type {} of {} for, allowed types: {}({})'.format(
                        self.odoo_type, self.odoo_attr, types, self.mapping))
            return function(self, *args, **kwargs)

        return wrapped

    return decorator


def normalize_format(datetime_format):
    return datetime_format.replace('yyyy', '%Y').replace('MM', '%m').replace(
        'dd', '%d').replace('HH', '%H').replace('mm', '%M').replace('ss', '%S')


class ConvertRule(object):

    def __init__(self, obj, mapping):
        super(ConvertRule, self).__init__()
        self.obj = obj
        self.mapping = mapping
        self.odoo_attr = mapping.odoo_attribute
        if '|' in self.odoo_attr:
            self.odoo_attr = self.odoo_attr.split('|')[-1]
        self.ext_attr = mapping.external_attribute
        self.additional_key = mapping.additional_key
        self._ext_type = None
        self._key = 'unknown'
        self._odoo_type = None
        self._odoo_value = None
        self._additional_info = {}

    def _convertUnknown(self, *args, **kwargs):
        return self.odoo_value

    def __getattr__(self, name):
        if not name.startswith('convert'):
            # Default behaviour
            raise AttributeError(
                '\'{class_name}\' object has no attribute \'{attr}\''.format(
                    class_name=self.__class__.__name__, attr=name))
        else:
            return self.convertUnknown

    @property
    def key(self):
        if self._key == 'unknown':
            self._key = (self.ext_attr and self.ext_attr.code or 'unknown')
        return self._key

    @key.setter
    def key(self, log):
        raise NotImplementedError('You can\'t set property key')

    @property
    def odoo_value(self):
        if not self._odoo_value:
            self._odoo_value = False
            if self.odoo_type == 'selection':
                values = {
                    x[0]: x[1]
                    for x in self.obj._fields[self.odoo_attr]
                    ._description_selection(self.obj.env)
                }
                self._odoo_value = values.get(
                    getattr(self.obj, self.odoo_attr), False)
            elif self.odoo_type in ('date', 'datetime'):
                self._odoo_value = \
                    self.obj._fields[self.odoo_attr].from_string(
                        getattr(self.obj, self.odoo_attr, False)
                    )
            else:
                self._odoo_value = getattr(self.obj, self.odoo_attr, False)
        return self._odoo_value

    @odoo_value.setter
    def odoo_value(self, log):
        raise NotImplementedError('You can\'t set property odoo_value')

    @property
    def odoo_type(self):
        if not self._odoo_type:
            self._odoo_type = self.obj._fields[self.odoo_attr].type
        return self._odoo_type

    @odoo_type.setter
    def odoo_type(self, log):
        raise NotImplementedError('You can\'t set property odoo_type')

    @property
    def ext_type(self):
        if not self._ext_type:
            self._ext_type = (self.ext_attr and self.ext_attr.type_id and
                              self.ext_attr.type_id.value or 'unknown')
        return self._ext_type

    @ext_type.setter
    def ext_type(self, log):
        raise NotImplementedError('You can\'t set property ext_type')

    @property
    def additional_info(self):
        if not self._additional_info:
            if not self.ext_attr.additional_info:
                self._additional_info = {}
            else:
                self._additional_info = json_loads(
                    self.ext_attr.additional_info)
        return self._additional_info

    @additional_info.setter
    def additional_info(self, log):
        raise NotImplementedError('You can\'t set property additional_info')

    @raise_bad_odoo_type(['integer', 'float'])
    def _convertInteger(self):
        return int(self.odoo_value)

    @raise_bad_odoo_type(('integer', 'float'))
    def _convertFloat(self):
        return float(self.odoo_value)

    @raise_bad_odoo_type(('boolean'))
    def _convertBoolean(self):
        return self.odoo_value

    @raise_bad_odoo_type(
        ('boolean', 'integer', 'float', 'char', 'text', 'html', 'date',
         'datetime', 'serialized', 'many2one', 'binary', 'selection'))
    def _convertText(self):
        if self.odoo_type in ('text', 'char') and not self.odoo_value:
            val = ''
        if self.odoo_type == 'many2one':
            if (self.additional_key and
                    hasattr(self.odoo_value, self.additional_key)):
                val = getattr(self.odoo_value, self.additional_key)
            else:
                raise NotImplementedError()
        else:
            val = self.odoo_value
        return ustr(val) if val else False

    @raise_bad_odoo_type(('date', 'datetime'))
    def _convertDate(self):
        val = self.odoo_value
        default = DATE_FORMAT
        if self.odoo_type == 'datetime':
            default = DATETIME_FORMAT
        _format = normalize_format(self.additional_info.get('format', default))
        return ustr(val.strftime(_format)) if val else False

    @raise_bad_odoo_type(('one2many'))
    def _convertComplex(self):
        result = []
        if bool(self.mapping.child_ids) and bool(self.odoo_value):
            for obj in self.odoo_value:
                sub_result = {}
                for child_mapping in self.mapping.child_ids:
                    convert_rule = ConvertRule(obj, child_mapping)
                    try:
                        value = convert_rule.process()
                        sub_result[convert_rule.key] = value
                    except NotImplementedError as err:
                        _logger.error(err)
                result.append(sub_result)
        return result

    def process(self):
        method_name = '_convert{}'.format(self.ext_type.strip().lower().title())
        method = getattr(self, method_name, None)
        result = self._convertUnknown()
        if method:
            result = method()
        return result
