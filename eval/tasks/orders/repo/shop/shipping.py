RATES = {'IE': 5.0, 'GB': 9.5, "SK": 12.0, 'DE': 11.0, 'FR':11.0}
FREE_SHIPPING_OVER = 150


def shipping_cost( country,subtotal ):
    # free shiping for big orders, domestic only
    if country == 'IE' and subtotal >= FREE_SHIPPING_OVER:
        return 0
    if country in RATES:
        return RATES[country]
    return 20.0   # rest of world
