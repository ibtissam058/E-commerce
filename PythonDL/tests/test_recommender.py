from retail_recommender.recommender import EventAwareRanker
from retail_recommender.schemas import EventContext, Product, RetailEvent


def test_discounted_item_ranks_first():
    products = [
        Product(source="x", external_id="1", title="Full price", url="https://x/1", current_price=100),
        Product(source="x", external_id="2", title="Deal", url="https://x/2", current_price=60, original_price=100),
    ]
    result = EventAwareRanker().recommend(products, EventContext(event=RetailEvent.BLACK_FRIDAY, urgency=.9))
    assert result[0].product.external_id == "2"
