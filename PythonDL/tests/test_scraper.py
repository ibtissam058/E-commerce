from bs4 import BeautifulSoup

from retail_recommender.scraper import RetailScraper, RetailerConfig


def test_json_ld_product_is_normalized():
    scraper = RetailScraper(RetailerConfig(name="shop", start_urls=["https://shop.example/sale"]))
    markup = '''<script type="application/ld+json">{
      "@context":"https://schema.org", "@type":"Product", "name":"Winter Coat",
      "sku":"coat-1", "offers":{"@type":"Offer", "price":"79.99", "priceCurrency":"USD", "availability":"InStock"},
      "aggregateRating":{"ratingValue":"4.6", "reviewCount":"120"}
    }</script>'''
    result = scraper._from_json_ld(BeautifulSoup(markup, "html.parser"), "https://shop.example/sale")
    assert len(result) == 1
    assert result[0].current_price == 79.99
    assert result[0].external_id == "coat-1"
    assert result[0].rating == 4.6
