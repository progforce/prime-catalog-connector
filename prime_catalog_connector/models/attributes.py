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
from __future__ import absolute_import
from openerp import api, fields, models
from json import loads as json_loads
from json import dumps as json_dumps


class ExternalServiceAttributeType(models.Model):
    _name = 'external.service.attribute.type'
    _rec_name = 'label'

    backend_id = fields.Many2one(
        'prime.catalog.backend',
        string='Service',
        required=True,
        ondelete='cascade',
        readonly=True,)
    value = fields.Char(
        string='Value',)
    label = fields.Char(
        string='Label',)

    @api.model
    def get_or_create(self, backend_id, value):
        domain = (['backend_id', '=', backend_id], ['value', '=', value],)
        exists = self.search(domain)
        if not bool(exists):
            exists = self.create({
                'backend_id': backend_id,
                'value': value,
                'label': value.capitalize()
            })

        return exists.id


class ExternalServiceAttribute(models.Model):
    _name = 'external.service.attribute'
    _rec_name = 'display_name'

    @api.multi
    @api.depends('parent_id')
    def _compute_display_name(self):
        for record in self:
            display_name = []
            if bool(record.parent_id):
                display_name += [record.parent_id.display_name]
            display_name += [record.code]
            record.display_name = ' | '.join(display_name)

    display_name = fields.Char(
        string='Display Name',
        store=True,
        compute='_compute_display_name',)
    backend_id = fields.Many2one(
        'prime.catalog.backend',
        string='Service',
        required=True,
        ondelete='cascade',
        readonly=True,)
    parent_id = fields.Many2one(
        'external.service.attribute',
        string='Parent',)
    code = fields.Char(
        string='Code',)
    type_id = fields.Many2one(
        'external.service.attribute.type',
        string='Type',)
    additional_info = fields.Text(string='Additional Info')
    child_ids = fields.One2many(
        'external.service.attribute',
        'parent_id',
        string='Child Attributes',)

    @api.model
    def delete_unused(self, vals):
        need_delete = [
            x for x in vals.keys() if x not in self.fields_get_keys()
        ]
        ret_vals = vals.copy()
        for key in need_delete:
            del ret_vals[key]
        return ret_vals

    @api.model
    def get_or_create(self, field):
        esat = self.env['external.service.attribute.type']
        keys = ['backend_id', 'parent_id', 'code']
        domain = tuple([[key, '=', value] for key, value in field.items()
                        if key in keys])
        exists = self.search(domain)
        if not bool(exists):
            if isinstance(field['type_id'], (str, unicode)):
                field['type_id'] = esat.get_or_create(field['backend_id'],
                                                      field['type_id'])
            exists = self.create(field)
        return exists.id

    @api.model
    def create_complex(self, attrs):
        result = []
        for attr in attrs:
            if attr.type_id.value == 'complex':
                info = json_loads(attr.additional_info)
                for row_code, row_data in info['fields'].items():
                    data = {
                        'backend_id': attr.backend_id.id,
                        'parent_id': attr.id,
                        'code': row_code,
                        'type_id': row_data['type'],
                        'additional_info': json_dumps(row_data),
                    }
                    f_id = self.get_or_create(data)
                    result.append(f_id)
        return self.browse(result)

    @api.model
    def create(self, vals):
        new_vals = self.delete_unused(vals)
        result = super(ExternalServiceAttribute, self).create(new_vals)
        self.create_complex(result)
        return result

    @api.multi
    def write(self, vals):
        new_vals = self.delete_unused(vals)
        return super(ExternalServiceAttribute, self).write(new_vals)

    _sql_constraints = [('name_uniq', 'unique(backend_id, code, parent_id)',
                         'ExternalServiceAttribute must be unique by code!')]

    _order = 'display_name asc'


class ExternalServiceAttributeMap(models.Model):
    _name = 'external.service.attribute.map'
    _rec_name = 'display_name'
    _default_model_name = 'product.template'

    @api.model
    def _get_odoo_attribute(self):
        obj = self.env[self._default_model_name]
        vals = [(x, obj._fields[x].string) for x in obj._fields.keys()]
        one2many_fields = {
            field: obj._fields[field].comodel_name
            for field in obj._fields if obj._fields[field].type == 'one2many'
        }
        sub_vals = []
        for field_name, field_model in one2many_fields.items():
            parent_obj = self.env[field_model]
            sub_selection = [('{}|{}'.format(field_name, x), '{} | {}'.format(
                obj._fields[field_name].string, parent_obj._fields[x].string))
                             for x in parent_obj._fields.keys()]
            sub_vals += sub_selection
        vals += sub_vals
        return sorted(vals, key=lambda tup: tup[1])

    @api.model
    def get_odoo_attribute_string(self, key):
        odoo_attributes = {
            attr[0]: attr[1]
            for attr in self._get_odoo_attribute()
        }
        return odoo_attributes.get(key, 'UNKNOWN')

    def get_odoo_attribute_model(self, obj_model_name, odoo_attribute):
        if not obj_model_name:
            obj_model_name = self._default_model_name
        obj = self.env[obj_model_name]
        one2many_fields = [(x, obj._fields[x].comodel_name) for x in obj._fields
                           if obj._fields[x].type == 'one2many']
        one2many_fields = {row[0]: row[1] for row in one2many_fields}
        return one2many_fields.get(odoo_attribute, self._default_model_name)

    @api.multi
    @api.depends('parent_id')
    def _compute_model_name(self):
        for record in self:
            obj_model_name = self._default_model_name
            if bool(record.parent_id):
                obj_model_name = record.parent_id.model_name
            record.model_name = record.get_odoo_attribute_model(
                obj_model_name, record.parent_id.odoo_attribute)

    @api.multi
    @api.depends('parent_id', 'odoo_attribute', 'external_attribute')
    def _compute_display_name(self):
        for record in self:
            display_name = []
            if bool(record.parent_id):
                display_name += [record.parent_id.display_name]
            display_name += [
                '{} -> {}'.format(
                    record.get_odoo_attribute_string(record.odoo_attribute),
                    record.external_attribute.display_name)
            ]
            record.display_name = ' |-> '.join(display_name)

    backend_id = fields.Many2one(
        'prime.catalog.backend',
        string='Service',
        required=True,)
    model_name = fields.Char(
        string='Model Name',
        compute='_compute_model_name',)
    parent_id = fields.Many2one(
        'external.service.attribute.map',
        string='Parent',)
    odoo_attribute = fields.Selection(
        selection='_get_odoo_attribute',
        string='Odoo Attribute',)
    external_attribute = fields.Many2one(
        'external.service.attribute',
        string='External Attribute',
        domain='[(\'backend_id\', \'=\', backend_id)]',
        required=True,)
    active = fields.Boolean(
        string='Active',
        default=False,)
    display_name = fields.Char(
        string='Display Name',
        store=True,
        compute='_compute_display_name',)
    additional_key = fields.Char(
        string='Additional Key',
        default=False,)
    child_ids = fields.One2many(
        'external.service.attribute.map', 'parent_id', string='Child Mapping')

    _order = 'display_name asc'
