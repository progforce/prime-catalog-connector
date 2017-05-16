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
from openerp import api, fields, models, _
from openerp.models import NewId
from openerp.exceptions import Warning as UserError
from openerp import SUPERUSER_ID
from random import randint
FAKER_FAILED_IMPORT = False
try:
    from faker import Faker
except ImportError:
    FAKER_FAILED_IMPORT = True


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    @api.multi
    def _compute_model_name(self):
        for record in self:
            record.model_name = self._model

    model_name = fields.Char(
        string='Model Name',
        compute='_compute_model_name',)


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _name = 'product.template'

    @api.multi
    def _compute_catalog_qty_by_locs(self):
        ptqbl = self.env['product.template.qty.by.locs'].sudo(SUPERUSER_ID)
        sl = self.env['stock.location']
        sq = self.env['stock.quant']
        for record in self:
            quants = sq.search([('product_id.product_tmpl_id', '=', record.id)])
            location_ids = list(set([x.location_id.id for x in quants]))
            lines = []
            if not isinstance(record.id, NewId):
                for location in sl.browse(location_ids):
                    line = ptqbl.create({
                        'location':
                        location.complete_name,
                        'qty':
                        record.with_context({
                            'location': location.id
                        }).qty_available,
                        'posx':
                        location.posx,
                        'posy':
                        location.posy,
                        'posz':
                        location.posz,
                        'is_scrap':
                        location.scrap_location,
                        'is_return':
                        location.return_location,
                        'type':
                        location.usage,
                    })
                    lines.append(line.id)
            record.catalog_qty_by_locs = lines

    @api.multi
    def _compute_catalog_pricing(self):
        ptp = self.env['product.template.pricing'].sudo(SUPERUSER_ID)
        rp = self.env['res.partner']
        desc_applied_on = self.env['product.pricelist.item']._fields[
            'applied_on']._description_selection(self.env)
        applied_on_map = {x[0]: x[1] for x in desc_applied_on}
        for record in self:
            lines = []
            if not isinstance(record.id, NewId):
                for price_list_item in record.item_ids:
                    customers = rp.search([('customer', '=', True),
                                           ('property_product_pricelist', '=',
                                            price_list_item.pricelist_id.id)])
                    for customer in customers:
                        description = 'Applied on {}'.format(
                            applied_on_map.get(price_list_item.applied_on,
                                               'Unknown'))
                        line = ptp.create({
                            'customer':
                            customer.name,
                            'pricelist':
                            price_list_item.pricelist_id.name,
                            'price':
                            price_list_item.fixed_price,
                            'description':
                            description,
                        })
                        lines.append(line.id)
            record.catalog_pricing = lines

    @api.multi
    def _compute_catalog_sales(self):
        pts = self.env['product.template.sales'].sudo(SUPERUSER_ID)
        sol = self.env['sale.order.line']
        for record in self:
            lines = []
            catalog_sales_qty = 0.0
            if not isinstance(record.id, NewId):
                sale_order_lines = sol.search([(
                    'product_tmpl_id', '=', record.id), ('state', '=', 'sale')])
                for sale_order_line in sale_order_lines:
                    sale_order = sale_order_line.order_id
                    line = pts.create({
                        'number':
                        sale_order.name,
                        'date':
                        sale_order.date_order,
                        'customer':
                        sale_order.partner_id.name,
                        'warehouse':
                        sale_order.warehouse_id.name,
                        'quantity':
                        sale_order_line.product_uom_qty,
                        'price':
                        sale_order_line.price_unit,
                        'status':
                        sale_order.state,
                    })
                    lines.append(line.id)
                    catalog_sales_qty += sale_order_line.product_uom_qty
            record.catalog_sales = lines
            record.catalog_sales_qty = catalog_sales_qty

    @api.multi
    def _compute_catalog_variants(self):
        ptv = self.env['product.template.variants'].sudo(SUPERUSER_ID)
        for record in self:
            lines = []
            if not isinstance(record.id, NewId):
                for obj in record.product_variant_ids:
                    line = ptv.create({
                        'attribute': 'default_code',
                        'value': obj.default_code,
                    })
                    lines.append(line.id)
            record.catalog_variants = lines

    @api.multi
    def _compute_model_name(self):
        for record in self:
            record.model_name = self._model

    sku = fields.Char(
        string='SKU',)
    catalog_qty_by_locs = fields.One2many(
        'product.template.qty.by.locs',
        string='QTY By Locs',
        compute='_compute_catalog_qty_by_locs',)
    catalog_pricing = fields.One2many(
        'product.template.pricing',
        string='Pricing',
        compute='_compute_catalog_pricing',)
    catalog_sales = fields.One2many(
        'product.template.sales',
        string='Sales',
        compute='_compute_catalog_sales',)
    catalog_sales_qty = fields.Float(
        string='salesQty',
        compute='_compute_catalog_sales',)
    catalog_variants = fields.One2many(
        'product.template.variants',
        string='Variants',
        compute='_compute_catalog_variants',)
    model_name = fields.Char(
        string='Model Name',
        compute='_compute_model_name',)

    @api.model
    def re_generate_skus(self):
        pts = self.search([])
        for pt in pts:
            pt.write({'sku': pt.generate_sku()})

    @api.model
    def generate_sku(self):
        return self.env['ir.sequence'].next_by_code('product.template')

    @api.model
    def create(self, vals):
        vals.update({'sku': self.generate_sku()})
        return super(ProductTemplate, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.sku and 'sku' not in vals:
            vals.update({'sku': self.generate_sku()})
        return super(ProductTemplate, self).write(vals)

    @api.multi
    def generate_demo_products(self, count):
        if FAKER_FAILED_IMPORT:
            raise UserError(_('Please first install `Faker` pip module'))
        fake = Faker()
        stock_quant = self.env['stock.quant']
        location_id = self.env.ref('stock.stock_location_components').id
        for idx in range(count):
            word = fake.word()
            product_template = self.create({'name': 'Product Template' + word})
            product1 = product_template.product_variant_ids[0]
            product1.type = 'product'
            product1.uom_id = self.env.ref('product.product_uom_unit')
            product1.uom_po_id = self.env.ref('product.product_uom_unit')
            product1.categ_id = self.env.ref('product.product_category_5')
            product1.default_code = product1.sku
            product1.name = 'Product Name ' + word
            product1.description = 'Product Description ' + word + str(idx + 1)
            stock_quant.create({
                'product_id': product1.id,
                'location_id': location_id,
                'qty': randint(0, 100),
            })
            product_template.list_price = randint(0, 1000)
            product_template.standard_price = randint(0, 1000)
            product_template.default_code = product_template.sku


class ProductTemplateQTYByLocs(models.TransientModel):
    _name = 'product.template.qty.by.locs'

    location = fields.Char(
        string='Location',)
    qty = fields.Float(
        string='QTY',)
    posx = fields.Integer(
        string='Corridor (X)',
        help='Optional localization details, for information purpose only')
    posy = fields.Integer(
        string='Shelves (Y)',
        help='Optional localization details, for information purpose only')
    posz = fields.Integer(
        string='Height (Z)',
        help='Optional localization details, for information purpose only')
    is_scrap = fields.Boolean(
        string='Is a Scrap Location?',
        help=('Check this box to allow using this location '
              'to put scrapped/damaged goods.'))
    is_return = fields.Boolean(
        string='Is a Return Location?',
        help=('Check this box to allow using this location '
              'as a return location.'))
    type = fields.Selection(
        [('supplier', 'Vendor Location'), ('view', 'View'),
         ('internal', 'Internal Location'), ('customer', 'Customer Location'), (
             'inventory', 'Inventory Loss'), ('procurement', 'Procurement'), (
                 'production', 'Production'), ('transit', 'Transit Location')],
        'Location Type',
        required=True,
        select=True,)


class ProductTemplatePricing(models.TransientModel):
    _name = 'product.template.pricing'

    customer = fields.Char(
        string='Customer',)
    pricelist = fields.Char(
        string='Pricelist',)
    price = fields.Float(
        string='Price',)
    description = fields.Char(
        string='Description',)


class ProductTemplateSales(models.TransientModel):
    _name = 'product.template.sales'

    number = fields.Char(
        string='Number',)
    date = fields.Datetime(
        string='Date',)
    customer = fields.Char(
        string='Customer',)
    warehouse = fields.Char(
        string='Warehouse',)
    quantity = fields.Float(
        string='Quantity',)
    price = fields.Float(
        string='Price',)
    status = fields.Char(
        string='Status',)


class ProductTemplateVariants(models.TransientModel):
    _name = 'product.template.variants'

    attribute = fields.Char(
        string='attribute',)
    value = fields.Char(
        string='value',)
