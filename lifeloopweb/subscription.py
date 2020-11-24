# pylint: disable=unused-argument
import json
import requests
from requests.auth import HTTPBasicAuth

from lifeloopweb import (config, logging, exception)

CONF = config.CONF
LOG = logging.get_logger(__name__)


class SubscriptionDriver(object):
    def get_customer(self, org_id):
        raise exception.MethodNotExists(self, "search_for_customer")

    def get_component_prices(self, component_id):
        raise exception.MethodNotExists(self, "get_component_prices")

    def get_product(self):
        raise exception.MethodNotExists(self, "get_product")

    def get_subscription(self, reference):
        raise exception.MethodNotExists(self, "get_subscription")

    def get_subscription_component_allocation(self, subscription_id):
        raise exception.MethodNotExists(
            self, "get_subscription_component_allocation")

    def update_license_quantity(self, org_id, quantity):
        raise exception.MethodNotExists(
            self, "update_license_quantity")

    def subscribe(self, user, org, form_data):
        raise exception.MethodNotExists(self, "subscribe")

    def get_discount(self, coupon):
        raise exception.MethodNotExists(self, "get_discount")

class ChargifyDriver(SubscriptionDriver):
    class __ChargifyDriver:
        PRODUCT_HANDLE = "leader-based-pricing"
        FAMILY_HANDLE = "toneo-inc-billing-plans"

        def __init__(self, organization_id):
            LOG.debug("Initializing ChargifyDriver")
            self._request_url = CONF.get("chargify.request.url")
            self._api_key = CONF.get("chargify.api.key")
            self.organization_id = organization_id

            # Cache elements
            self.product_data = {}
            self.customer_data = {}
            self.subscription_data = {}
            self.discount = None

            super().__init__()

        def get_customer(self, org_id):
            """ API docs:
            https://reference.chargify.com/v1/customers/search-for-customer
            """
            if not self.customer_data:
                LOG.debug("Get customer by org_id: %s", org_id)
                response = self.get(
                    "/customers.json?q={}".format(org_id))
                if response.json():
                    self.customer_data = response.json()[0]['customer']
            return self.customer_data

        def get_component_prices(self, component_id=None):
            """ API docs:
            https://reference.chargify.com/v1/components/
            list-specific-component-for-a-product-family
            """
            if not component_id:
                component_id = CONF.get('chargify.default.component.id')
            LOG.debug("Trying to get component's prices by component id: %s", component_id)
            product = self.get_product()
            if product:
                product_family_id = product["product_family"]["id"]
                response = self.get(
                    "/product_families/%s/components/%s.json" %
                    (product_family_id, component_id))
                if response.status_code != 404:
                    return response.json()["component"]["prices"]
            return []

        def get_product(self):
            """ API docs:
            https://reference.chargify.com/v1/products/
            read-the-product-via-api-handle#read-product-via-api-handle
            """
            if not self.product_data:
                LOG.debug("Trying to get product by handle: %s", self.PRODUCT_HANDLE)
                response = self.get("/products/handle/%s.json" % self.PRODUCT_HANDLE)
                if response.status_code != 200:
                    return []
                self.product_data = response.json()["product"]
            return self.product_data

        def get_discount(self, coupon):
            """ API docs:
            https://reference.chargify.com/v1/coupons-editing/finding-a-coupon
            """
            if not self.discount:
                product = self.get_product()
                if product:
                    product_family_id = product["product_family"]["id"]
                    LOG.debug("Trying to get discount by product id ("
                              "%s) and coupon name (%s)", product_family_id, coupon)
                    response = self.get("/product_families/%s/coupons/find.json?code=%s"
                                        % (product_family_id, coupon))
                if response.status_code == 200:
                    self.discount = response.json()['coupon']['percentage']
            return self.discount

        def get_subscription(self, reference):
            """ Returns all subscription details for selected customer
            API docs:
            https://reference.chargify.com/v1/subscriptions/list-by-customer
            #list-by-customer
            """
            if not self.subscription_data:
                LOG.debug("Trying to get subscription data by org_id: %s", reference)
                customer = self.get_customer(reference)
                if customer:
                    response = self.get(
                        "/customers/%s/subscriptions.json" % customer['id'])
                    if (response.status_code == 200 and
                            response.json() and
                            'subscription' in response.json()[0] and
                            response.json()[0]['subscription']['state'] != 'canceled'):
                        return response.json()[0]['subscription']
            return {}

        def get_subscription_component_allocation(self, subscription_id):
            """ API docs:
            https://reference.chargify.com/v1/components-quantity-allocations
            /retrieve-allocations-for-a-component-by-subscription
            """
            LOG.debug("Trying to get license allocation quantity by subscription data id:"
                      " %s", subscription_id)
            component_id = CONF.get('chargify.default.component.id')
            response = self.get(
                "/subscriptions/%s/components/%s/allocations.json" %
                (subscription_id, component_id))
            if response.status_code == 200 and 'allocation' in response.json()[0]:
                return response.json()[0]['allocation']
            return {'quantity': 0}

        def update_license_quantity(self, org_id, quantity):
            """ API docs:
            https://reference.chargify.com/v1/components-quantity-allocations
            /updating-the-quantity#updating-the-quantity
            """
            subscription_data = self.get_subscription(org_id)
            if subscription_data:
                subscription_id = subscription_data['id']
                LOG.debug("Trying to update license allocation by subscription data id"
                          " %s", subscription_id)
                component_id = CONF.get('chargify.default.component.id')
                allocation = {
                    "component_id": component_id,
                    "quantity": quantity
                }
                response = self.post(
                    "/subscriptions/%s/components/%s/allocations.json" %
                    (subscription_id, component_id),
                    data=json.dumps({"allocation": allocation}))
                return response.json()
            return False

        def update_card_info(self, org_id, form_data):
            """ API docs:
            https://reference.chargify.com/v1/subscriptions/create-subscription
            #subscription-with-quantity-based-component
            """
            subscription_data = self.get_subscription(org_id)
            subscription_id = subscription_data['id']
            LOG.debug("Trying to update customer by subscription data id %s",
                      str(subscription_id))
            self.subscription_data = {}
            subscription = {
                "credit_card_attributes": {
                    "full_number": form_data["full_number"],
                    "expiration_month": form_data["expiration_month"],
                    "expiration_year": form_data["expiration_year"],
                    "billing_address": form_data["billing_address"],
                    "billing_city": form_data["billing_city"],
                    "billing_state": form_data["billing_state"],
                    "billing_country": form_data["billing_country"],
                    "billing_zip": form_data["billing_zip"]}}
            response = self.put("/subscriptions/%s.json" % subscription_id,
                                data=json.dumps({"subscription": subscription}))
            return response.json()

        def cancel(self, org_id):
            subscription_data = self.get_subscription(org_id)
            response = self.post("/subscriptions/%s/delayed_cancel.json"
                                 % subscription_data['id'])
            self.subscription_data = {}
            if response.status_code != 200:
                return False
            return True

        def stop_cancellation(self, org_id):
            subscription_data = self.get_subscription(org_id)
            response = self.delete("/subscriptions/%s/delayed_cancel.json"
                                   % subscription_data['id'])
            self.subscription_data = {}
            if response.status_code != 200:
                return False
            return True

        def subscribe(self, user, org, form_data):
            """ API docs:
            https://reference.chargify.com/v1/subscriptions/create-subscription
            #subscription-with-quantity-based-component
            """
            LOG.debug("Trying to subscribe customer by org_id %s", str(org.id))
            subscription = {
                "product_handle": self.PRODUCT_HANDLE,
                "customer_attributes": {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "organization": org.name,
                    "email": user.email,
                    "reference": str(org.id)},
                "credit_card_attributes": {
                    "full_number": form_data["full_number"],
                    "expiration_month": form_data["expiration_month"],
                    "expiration_year": form_data["expiration_year"],
                    "billing_address": form_data["billing_address"],
                    "billing_city": form_data["billing_city"],
                    "billing_state": form_data["billing_state"],
                    "billing_country": form_data["billing_country"],
                    "billing_zip": form_data["billing_zip"]},
                "components": [{
                    "component_id": CONF.get('chargify.default.component.id'),
                    "allocated_quantity": 1}],
                "coupon_code": form_data['coupon_code']}
            response = self.post("/subscriptions.json",
                                 data=json.dumps({"subscription": subscription}))
            return response.json()

        def get(self, api_url, data=None):
            """ Make GET request """
            return self._call_api("GET", api_url, data)

        def post(self, api_url, data=None):
            """ Make POST request """
            return self._call_api("POST", api_url, data)

        def put(self, api_url, data=None):
            """ Make PUT request """
            return self._call_api("PUT", api_url, data)

        def delete(self, api_url, data=None):
            """ Make PUT request """
            return self._call_api("DELETE", api_url, data)

        def _call_api(self, method, api_url, data):
            """ Chargify API call """
            kwargs = {"headers": {"Accept": "application/json",
                                  "Content-Type": "application/json"},
                      "auth": HTTPBasicAuth(self._api_key, "x")}
            if data:
                kwargs["data"] = data
            request = requests.request(
                method, self._request_url + api_url, **kwargs)
            return request

    instance = None

    def __new__(cls, organization_id): # __new__ always a classmethod
        if not ChargifyDriver.instance or ChargifyDriver.instance.organization_id != organization_id:
            ChargifyDriver.instance = ChargifyDriver.__ChargifyDriver(organization_id)
        return ChargifyDriver.instance
    def __getattr__(self, name):
        return getattr(self.instance, name)
    def __setattr__(self, name, value):
        return setattr(self.instance, name, value)
