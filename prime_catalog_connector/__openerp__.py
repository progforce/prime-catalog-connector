# -*- coding: utf-8 -*-
# © 2017 Progforce, LLC
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    'name':
    'Prime Catalog Connector',
    'summary':
    'Connector module for `Prime Catalog`',
    'version':
    '9.0.0.0.1',
    'sequence':
    10,
    'author':
    'Progforce, LLC',
    'website':
    'https://github.com/progforce/prime-catalog-connector.git#9.0',
    'license':
    'GPL-3',
    'category':
    'Connector',
    'images': [
        'images/create_new_backend_1.png', 'images/create_new_backend_2.png',
        'images/revoke_token.png', 'images/synchronize_metadata.png'
    ],
    'depends': [
        'connector',
        'product',
        'stock',
        'purchase',
        'sale',
    ],
    'data': [
        'views/prime_catalog_backend_views.xml',
        'views/product_template_view.xml',
        'data/ir_sequence.xml',
        'security/prime_catalog_connector_security.xml',
        'security/ir.model.access.csv',
    ],
    # 'demo': [
    #     'demo/prime_catalog_demo.xml',
    # ],
    'installable':
    True,
    'application':
    True,
    'auto_install':
    False,
}
