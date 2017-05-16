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
import requests
from six.moves.urllib.parse import urlsplit, urlunsplit
from json import dumps as json_dumps

from itertools import groupby

from openerp import api, fields, models, _
from openerp.addons.connector.unit.backend_adapter import BackendAdapter
from openerp.addons.connector.connector import ConnectorEnvironment
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.event import (on_record_create, on_record_write,
                                            on_record_unlink)
from openerp.addons.connector.exception import RetryableJobError
from openerp.exceptions import Warning as UserError
from openerp import SUPERUSER_ID

from ..backend import prime_catalog
from ..utils.converter import ConvertRule
import base64
from csv import DictReader
from requests.exceptions import ConnectionError
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import logging

_logger = logging.getLogger(__name__)


def read(obj, field_names):
    res = obj.read([x for x in field_names if '.' not in x], load=None)

    related_fields = [x for x in field_names if '.' in x]

    for field, nested in groupby(related_fields, lambda x: x.split('.')[0]):
        field_id = obj.read([field], load=None)[0][field]
        field_model = obj.fields_get([field])[field]['relation']
        nested_fields = ['.'.join(x.split('.')[1:]) for x in nested]
        field_res = read(obj.env[field_model].browse(field_id), nested_fields)
        res[0].update({field: field_res[0]})

    return res


def url_path_join(*parts):
    """Normalize url parts and join them with a slash."""
    schemes, netlocs, paths, queries, fragments = \
        zip(*(urlsplit(part) for part in parts))
    scheme = first(schemes)
    netloc = first(netlocs)
    path = '/'.join(x.strip('/') for x in paths if x)
    query = first(queries)
    fragment = first(fragments)
    return urlunsplit((scheme, netloc, path, query, fragment))


def first(sequence, default=''):
    return next((x for x in sequence if x), default)


def backends(session, backend_ids=None):
    domain = []
    if backend_ids:
        if isinstance(backend_ids, (int, long)):
            backend_ids = [backend_ids]
        if not isinstance(backend_ids, (tuple, list)):
            raise NotImplementedError
        domain += [('id', 'in', backend_ids)]
    return session.env['prime.catalog.backend'].sudo(SUPERUSER_ID).search(
        domain)


@prime_catalog
class PrimeCatalogService(BackendAdapter):
    _model_name = 'prime.catalog.service'

    def get_headers(self):
        return {'Authorization': 'Bearer {token}'.format(token=self.token)}

    @property
    def conf(self):
        return self.env['catalog.urls.config.settings']

    @conf.setter
    def conf(self, conf):
        raise NotImplementedError('You can\'t set conf')

    @property
    def base_api_url(self):
        return url_path_join(self.url, self.conf.get('base_api_url'))

    @base_api_url.setter
    def base_api_url(self, base_api_url):
        raise NotImplementedError('You can\'t set base_api_url')

    @property
    def post_product_url(self):
        return url_path_join(self.base_api_url,
                             self.conf.get('post_product_url'))

    @post_product_url.setter
    def post_product_url(self, post_product_url):
        raise NotImplementedError('You can\'t set post_product_url')

    @property
    def get_json_keys_url(self):
        return url_path_join(self.base_api_url,
                             self.conf.get('get_json_keys_url'))

    @get_json_keys_url.setter
    def get_json_keys_url(self, get_json_keys_url):
        raise NotImplementedError('You can\'t set get_json_keys_url')

    @property
    def revoke_token_url(self):
        return url_path_join(self.base_api_url,
                             self.conf.get('revoke_token_url'))

    @revoke_token_url.setter
    def revoke_token_url(self, revoke_token_url):
        raise NotImplementedError('You can\'t set revoke_token_url')

    @property
    def mapping_csv_url(self):
        return url_path_join(self.base_api_url,
                             self.conf.get('mapping_csv_url'))

    @mapping_csv_url.setter
    def mapping_csv_url(self, mapping_csv_url):
        raise NotImplementedError('You can\'t set mapping_csv_url')

    def revoke_token(self, login, password):
        token = None
        headers = {
            'login': login,
            'password': password,
        }
        response = requests.post(self.revoke_token_url, headers=headers)
        if response.status_code == 200 and response.reason == 'OK':
            response_json = response.json()
            if response_json and 'token' in response_json:
                token = response_json['token']
        if token is None:
            raise NotImplementedError('Failed revoke Token!')
        return token

    def get_product_data(self, product):
        result = {}
        for mapping in self.attrs_info['map']:
            convert_rule = ConvertRule(product, mapping)
            try:
                value = convert_rule.process()
                result[convert_rule.key] = value
            except NotImplementedError as err:
                _logger.error(err)
        return self.filter_product_data(result)

    def get_mapping(self):
        headers = self.get_headers()
        response = requests.get(self.get_json_keys_url, headers=headers)
        return response.json()

    def get_map_file(self):
        headers = self.get_headers()
        response = requests.get(self.mapping_csv_url, headers=headers)
        return base64.b64encode(response.content)

    def filter_product_data(self, product_data):
        result = product_data.copy()
        mapping = self.get_mapping()
        active_keys = mapping['keys']
        to_delete_keys = []
        for key in result:
            if key not in active_keys:
                to_delete_keys += [key]
        for key in to_delete_keys:
            del result[key]
        return result

    def post_product(self, product_data):
        headers = self.get_headers()
        headers.update({'content-type': 'application/json'})
        requests.post(
            self.post_product_url,
            data=json_dumps(product_data),
            headers=headers)

    def write_quant(self, quant):
        quant.product_id.product_tmpl_id.write({
            'name':
            quant.product_id.product_tmpl_id.name,
        })

    def delete_quant(self, quant):
        quant.product_id.product_tmpl_id.write({
            'name':
            quant.product_id.product_tmpl_id.name,
        })


class PrimeCatalogBackend(models.Model):
    _name = 'prime.catalog.backend'
    _inherit = 'connector.backend'

    _backend_type = 'prime_catalog'

    @api.model
    def _get_test_method(self):
        test_methods = [
            method for method in dir(self)
            if callable(getattr(self, method)) and
            method.startswith('catalog_api_')
        ]
        return [(x, x.replace('catalog_api_', '')) for x in test_methods]

    version = fields.Selection(selection_add=[('0.1', '0.1')])
    url = fields.Char(required=True)
    counter_demo_product = fields.Integer(
        string='Count',
        default=1000,)
    login = fields.Char(
        string='Login',)
    password = fields.Char(
        string='Password',)
    show_password = fields.Boolean(
        string='Show Password',
        default=True,)
    token = fields.Char(
        string='Token',)
    show_token = fields.Boolean(
        string='Show Token',
        default=True,)
    test_method = fields.Selection(_get_test_method, string='Test Method')
    mapping_file = fields.Binary(
        string='Mapping file',)

    @api.multi
    def revoke_token(self):
        self.ensure_one()
        session = ConnectorSession.from_env(self.env)
        env = ConnectorEnvironment(self, session, 'prime.catalog.service')
        service = env.get_connector_unit(PrimeCatalogService)
        service.url = self.url
        try:
            token = service.revoke_token(self.login, self.password)
        except NotImplementedError as err:
            raise UserError(str(err))
        self.write({'token': token})

    @api.multi
    def export_products(self):
        self.ensure_one()
        model_name = 'product.template'
        session = ConnectorSession.from_env(self.env)
        products = session.env[model_name].search([])
        for product in products:
            export_product_job.delay(session, model_name, self.id, product.id)

    @api.multi
    def delete_products(self):
        self.ensure_one()
        model_name = 'product.template'
        session = ConnectorSession.from_env(self.env)
        products = session.env[model_name].search([])
        for product in products:
            delete_product_job.delay(session, model_name, self.id, product.id)

    @api.multi
    def generate_demo_products(self):
        count = self.counter_demo_product or 1000
        self.env['product.template'].generate_demo_products(count)

    @api.multi
    def test_job(self):
        method_name = self.test_method
        test_method = getattr(self, method_name, None)
        if test_method:
            test_method()
        return True

    @api.multi
    def catalog_api_load_mapping(self):
        self.ensure_one()
        session = ConnectorSession.from_env(self.env)
        env = ConnectorEnvironment(self, session, 'prime.catalog.service')
        service = env.get_connector_unit(PrimeCatalogService)
        service.url = self.url
        service.token = self.token
        esa = self.env['external.service.attribute']
        mapping = service.get_mapping()
        clear_fields = {
            key: value
            for key, value in mapping.items() if isinstance(value, dict)
        }
        for code, data in clear_fields.items():
            field = {
                'backend_id': self.id,
                'parent_id': False,
                'code': code,
                'type_id': data['type'],
                'additional_info': json_dumps(data)
            }
            esa.get_or_create(field)

    @api.model
    def parse_map_file(self):
        reader = DictReader(StringIO(base64.b64decode(self.mapping_file)))
        rows = [row for row in reader]
        return rows

    @api.model
    def get_map_file(self):
        self.mapping_file = False
        session = ConnectorSession.from_env(self.env)
        env = ConnectorEnvironment(self, session, 'prime.catalog.service')
        service = env.get_connector_unit(PrimeCatalogService)
        service.url = self.url
        service.token = self.token
        self.mapping_file = service.get_map_file()

    @api.model
    def check_map_file(self):

        def err():
            message = (
                'Bad Mapping File!\n'
                'Correct Mapping file is CSV format file with 3 columns:\n'
                '\n'
                '"parent_odoo_attr","odoo_attr","parent_ext_attr",'
                '"ext_attr","additional_key","active"\n'
                '"parent_odoo_attr_1","odoo_attr_1","parent_ext_attr_1",'
                '"ext_attr_1","additional_key_1","active"\n'
                '...\n'
                '"parent_odoo_attr_n","odoo_attr_n","parent_ext_attr_n",'
                '"ext_attr_n","additional_key_n","active"\n')
            raise UserError(_(message))

        if not self.mapping_file:
            err()

        reader = DictReader(StringIO(base64.b64decode(self.mapping_file)))
        if reader.fieldnames != [
                'parent_odoo_attr', 'odoo_attr', 'parent_ext_attr', 'ext_attr',
                'additional_key', 'active'
        ]:
            err()

    @api.model
    def create_map_row(self, attr, parent_id=False):

        def str2bool(v):
            return v.lower() in ('yes', 'true', 't', '1')

        def domain(add):
            domain = [('backend_id', '=', self.id)]
            return domain + add

        esam_obj = self.env['external.service.attribute.map']
        esa_obj = self.env['external.service.attribute']
        #
        parent_ext_attr_id = False
        parent_ext_attr = attr['parent_ext_attr'].strip()
        if parent_ext_attr:
            parent_ext_attr_id = esa_obj.search(
                domain([('code', '=', parent_ext_attr)]))
            parent_ext_attr_id = bool(
                parent_ext_attr_id) and parent_ext_attr_id.id
        #
        ext_attr_id = False
        ext_attr = attr['ext_attr'].strip()
        if ext_attr:
            ext_attr_id = esa_obj.search(
                domain([('parent_id', '=', parent_ext_attr_id), ('code', '=',
                                                                 ext_attr)]))
            ext_attr_id = bool(ext_attr_id) and ext_attr_id.id
        #
        odoo_attrs = esam_obj._get_odoo_attribute()
        odoo_attr = attr['odoo_attr'].strip()
        exist_odoo_attr = False
        for o_attr in odoo_attrs:
            condition = o_attr[0] == odoo_attr
            if parent_id:
                parent = esam_obj.browse(parent_id).odoo_attribute
                condition = o_attr[0] == '{}|{}'.format(parent, odoo_attr)
            if condition:
                exist_odoo_attr = o_attr[0]
                break
        #
        active = str2bool(attr['active'].strip())
        #
        additional_key = attr['additional_key'].strip()

        already_exists = esam_obj.search(
            domain([('parent_id', '=', parent_id), (
                'odoo_attribute', '=', exist_odoo_attr), ('external_attribute',
                                                          '=', ext_attr_id)]))
        condition = (exist_odoo_attr and ext_attr_id)
        if condition:
            if not bool(already_exists):
                already_exists = esam_obj.create({
                    'backend_id':
                    self.id,
                    'parent_id':
                    parent_id,
                    'odoo_attribute':
                    exist_odoo_attr,
                    'external_attribute':
                    ext_attr_id,
                    'active':
                    active,
                    'additional_key':
                    additional_key,
                })
        return already_exists.id

    @api.model
    def catalog_api_load_map_file(self):

        def get_tree(lines):
            raw_childs = [x for x in lines if x['parent_odoo_attr'].strip()]
            childs = {}
            for row in raw_childs:
                if row['parent_odoo_attr'] not in childs:
                    childs[row['parent_odoo_attr']] = []
                childs[row['parent_odoo_attr']] += [row]
            result_lines = []
            main = [x for x in lines if x not in raw_childs]
            for line in main:
                new_line = line.copy()
                new_line['childs'] = childs.get(line['odoo_attr'], [])
                result_lines += [new_line]
            return result_lines

        self.get_map_file()
        self.check_map_file()
        self.catalog_api_load_mapping()
        rows = get_tree(self.parse_map_file())
        for row in rows:
            row_id = self.create_map_row(row, False)
            for child_row in row['childs']:
                self.create_map_row(child_row, row_id)

        return True

    @api.model
    def get_attr_info(self):
        attribute_types = self.env['external.service.attribute.type'].search([(
            'backend_id', '=', self.id)])
        attribute_values = self.env['external.service.attribute'].search([(
            'backend_id', '=', self.id)])
        attribute_map = self.env['external.service.attribute.map'].search([(
            'backend_id', '=', self.id), ('parent_id', '=', False)])
        attribute = {
            'types': attribute_types,
            'values': attribute_values,
            'map': attribute_map,
        }
        return attribute

    @api.multi
    def synchronize_metadata(self):
        for row in self:
            if not row.token:
                raise UserError(_('Please Revoke Token First'))
            row.catalog_api_load_map_file()


@job
def export_product_job(session, model_name, backend_id, product_id):
    backend = backends(session, backend_id)
    env = ConnectorEnvironment(backend, session, 'prime.catalog.service')
    service = env.get_connector_unit(PrimeCatalogService)
    service.url = backend.url
    service.token = backend.token
    service.attrs_info = backend.get_attr_info()

    if product_id:
        product = session.env[model_name].browse(product_id)
        try:
            product_data = service.get_product_data(product)
            service.post_product(product_data)
        except ConnectionError:
            raise RetryableJobError('Failed Connect to Catalog!')


@job
def delete_product_job(session, model_name, backend_id, product_id):
    backend = backends(session, backend_id)
    env = ConnectorEnvironment(backend, session, 'prime.catalog.service')
    service = env.get_connector_unit(PrimeCatalogService)
    service.url = backend.url
    service.token = backend.token

    if product_id:
        product_data = {
            'id': str(product_id),
            'delete': True,
        }
        try:
            service.post_product(product_data)
        except Exception:
            raise RetryableJobError('Failed Post Product')


@on_record_create(model_names='product.template')
@on_record_write(model_names='product.template')
def delay_export_product(session, model_name, record_id, vals):
    for backend in backends(session):
        export_product_job.delay(session, 'product.template', backend.id,
                                 record_id)


@on_record_unlink(model_names='product.template')
def delay_delete_product(session, model_name, record_id):
    for backend in backends(session):
        delete_product_job.delay(session, 'product.template', backend.id,
                                 record_id)
