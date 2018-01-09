import json

from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.serializers.json import DjangoJSONEncoder


def extract_variant_image_data(image, description=None):
    """Extracts ImageObject data from variant's image."""
    return {
        "@context": "http://schema.org",
        "@type": "ImageObject",
        "contentUrl": image.thumbnail['540x540'].url,
        "description": description or image.name,
        "width": 540,
        "height": 540
    }


def extract_variant_offer_data(stock_info, description, variant, category):
    """Extracts data for schema.org 'Offer' markup, from ProductVariant data."""
    offer_data = {
        '@type': 'Offer',
        'itemCondition': 'http://schema.org/NewCondition',
        'description': description,
        'name': str(variant),
        'gtin13': variant.sku,
        'category': category}
    if stock_info:
        offer_data.update({
            'price': stock_info.price.gross,
            'priceCurrency': stock_info.price.currency,
        })
    if stock_info and stock_info.quantity > 0:
        offer_data['availability'] = 'http://schema.org/InStock'
    else:
        offer_data['availability'] = 'http://schema.org/OutOfStock'
    return offer_data


def get_product_json_ld_data(product, variants_with_stock_info, currency):
    """Generates JSON-LD data for product."""
    offers = []
    prices = []

    product_image = None
    if product.main_image:
        product_image = product.main_image.image
    for variant, stock_info in variants_with_stock_info:
        if stock_info:
            prices.append(stock_info.price.gross)
        variant_data = extract_variant_offer_data(
            stock_info=stock_info,
            description=product.description,
            category=str(product.category),
            variant=variant)

        image = variant.get_first_image() or product_image
        if image:
            variant_data['image'] = extract_variant_image_data(image)

        offers.append(variant_data)

    product_availability = 'http://schema.org/OutOfStock'
    for offer in offers:
        if offer['availability'] == 'http://schema.org/InStock':
            product_availability = offer['availability']
            break

    main_entity = {
        '@type': 'Product',
        'name': str(product),
        'description': product.description,
        'offers': {
            '@type': 'AggregateOffer',
            'availability': product_availability,
            'priceCurrency': currency,
            'sku': product.pk,
            'category': str(product.category),
            'offerCount': len(offers),
            'offers': offers
        }
    }
    if prices:
        main_entity['offers']['lowPrice'] = min(prices)
        main_entity['offers']['highPrice'] = max(prices)


    if product_image:
        main_entity['offers']['image'] = extract_variant_image_data(
            product_image, description=product.name)
    return json.dumps(main_entity, cls=DjangoJSONEncoder)


def get_collection_json_ld_data(variants_with_data, category=None,
                                default_name=None):
    """Generates JSON-LD data for collection of Products.
    eg. category/search page.
    """
    items = []
    for position, (variant, _, stock_info) in enumerate(variants_with_data, start=1):
        variant_data = {
            '@type': 'Product',
            "description": ' ' or str(variant.product.description),
            "name": str(variant)
        }

        variant_data['offers'] = extract_variant_offer_data(
            stock_info=stock_info,
            description=' ' or variant.product.description,
            category=str(category or variant.product.category),
            variant=variant)

        variant_image = variant.get_first_image()
        if variant_image:
            variant_data['offers']['image'] = extract_variant_image_data(
                variant_image, description=variant.name)

        items.append(variant_data)

    data = {
        "@context": "http://schema.org",
        "@type": "Offer",
        "itemOffered": items,
    }
    if category:
        data.update({
            "name": category.name,
            "url": category.get_absolute_url(),
            "description": category.description,
            "category": str(category),
        })

    if default_name:
        data['name'] = default_name
    return json.dumps(data, cls=DjangoJSONEncoder)
