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
from openerp.addons.connector.connector import ConnectorEnvironment
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.event import (on_record_create, on_record_write,
                                            on_record_unlink)
from .prime_catalog_backend import (backends, PrimeCatalogService)


@job
def export_stock_quant_job(session, model_name, backend_id, quant_id=None):
    backend = backends(session, backend_id)
    env = ConnectorEnvironment(backend, session, 'prime.catalog.service')
    service = env.get_connector_unit(PrimeCatalogService)
    service.url = backend.url

    if quant_id:
        quants = session.env[model_name].browse(quant_id)
        for quant in quants:
            service.write_quant(quant)


@job
def delete_stock_quant_job(session, model_name, backend_id, quant_id=None):
    backend = backends(session, backend_id)
    env = ConnectorEnvironment(backend, session, 'prime.catalog.service')
    service = env.get_connector_unit(PrimeCatalogService)
    service.url = backend.url

    quants = []
    if quant_id:
        quants = session.env[model_name].browse(quant_id)
        for quant in quants:
            service.delete_quant(quant)


@on_record_create(model_names='stock.quant')
@on_record_write(model_names='stock.quant')
def delay_export_quant(session, model_name, record_id, vals):
    for backend in backends(session):
        export_stock_quant_job.delay(session, 'stock.quant', backend.id,
                                     record_id)


@on_record_unlink(model_names='stock.quant')
def delay_delete_quant(session, model_name, record_id, vals):
    for backend in backends(session):
        delete_stock_quant_job.delay(session, 'stock.quant', backend.id,
                                     record_id)
