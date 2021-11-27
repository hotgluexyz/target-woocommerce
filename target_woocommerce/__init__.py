#!/usr/bin/env python3
import os
import json
import argparse
import logging
from woocommerce import API

logger = logging.getLogger("target-WooCommerce")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class InputError(Exception):
    pass


def load_json(path):
    with open(path) as f:
        return json.load(f)


def parse_args():
    '''Parse standard command-line args.
    Parses the command-line arguments mentioned in the SPEC and the
    BEST_PRACTICES documents:
    -c,--config     Config file
    -s,--state      State file
    -d,--discover   Run in discover mode
    -p,--properties Properties file: DEPRECATED, please use --catalog instead
    --catalog       Catalog file
    Returns the parsed args object from argparse. For each argument that
    point to JSON files (config, state, properties), we will automatically
    load and parse the JSON file.
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-c', '--config',
        help='Config file',
        required=True)

    args = parser.parse_args()
    if args.config:
        setattr(args, 'config_path', args.config)
        args.config = load_json(args.config)

    return args


def initialize_woocommerce_client(config):
    config['url'] = config.get('site_url')
    config['version'] = "wc/v3"
    client = API(**config)
    return client


def upload_products(client, input_path):
    # Read the products
    products = load_json(input_path)

    for product in products:
        # Check if type is simple or variable
        product_type = "variable" if product.get('variants') else "simple"
        product_data = dict(
            name = product.get('title'),
            description = product.get('body_html'),
            type = product_type,
            short_description = product.get('body_html'),
            images = product.get('images'),
            regular_price = product.get('price'),
            sku = product.get('sku'),
            stock_quantity = product.get('inventory_quantity')
        )

        # Insert product in it's category
        res = client.get("products/categories")
        if res.status_code>=400:
            raise InputError(json.loads(res.content).get("message"))
        products_types = client.get("products/categories").json()
        type_names = [p['name'] for p in products_types]
        if product.get("product_type") not in type_names:
            product_type = dict(name=product.get("product_type"))
            res = client.post("products/categories", product_type)
            type_id = json.loads(res.text).get('id')
        else:
            type_id = next(a.get("id") for a in products_types if a.get("name")==product.get("product_type"))
        
        if type_id:
            product_data["categories"] = [{"id": type_id}]
        res = client.post("products", product_data)
        if res.status_code>=400:
            raise InputError(json.loads(res.content).get("message"))
        product_id = json.loads(res.text).get('id')
    
    # If type is variable
    if product_type == "variable":
        
        # Create and insert the atributes into the product
        mandatory_fields = ["sku", "price", "inventory_quantity", "title"]
        variant_attributes = [k for v in product['variants'] for k in v.keys() if k not in mandatory_fields]
        variant_attributes = list(set(variant_attributes))
        
        attributes = []
        for attribute in variant_attributes:
            options = [v.get(attribute) for v in product['variants']]
            data = dict(
                name=attribute,
                position=0,
                visible=False,
                variation=True,
                options=options
            )
            attributes.append(data)
        # Update the product with the variants
        attribute_dict = {"attributes": attributes}
        res = client.put(f"products/{product_id}", attribute_dict)
        if res.status_code>=400:
            raise InputError(json.loads(res.content).get("message"))
        
        # Insert the variants
        for variant in product['variants']:
            attributes = [{"name": a, "option": variant[a]} for a in variant_attributes]
            product_variation = dict(
                description = variant.get('title'),
                regular_price = variant.get('price'),
                sku = variant.get('sku'),
                manage_stock = True,
                stock_quantity = variant.get('inventory_quantity'),
                attributes = attributes
            )
            res = client.post(f"products/{product_id}/variations", product_variation)
            if res.status_code>=400:
                raise json.loads(res.content).get("message")


def upload(client, config):
    # Get input path
    input_path = f"{config['input_path']}/products.json"
    if os.path.exists(input_path):
        logger.info("Found products.json, uploading...")
        try:
            upload_products(client, input_path)
            logger.info("products.json uploaded!")
        except InputError as e:
            logger.error(f"Upload Error: {e}")
        logger.info("Posting process has completed!")


def main():
    # Parse command line arguments
    args = parse_args()
    config = args.config

    # Authorize WooCommerce client
    client = initialize_woocommerce_client(config)

    # Upload the WooCommerce data
    upload(client, config)


if __name__ == "__main__":
    main()
