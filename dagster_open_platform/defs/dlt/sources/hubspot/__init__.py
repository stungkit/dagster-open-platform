"""This is a module that provides a DLT source to retrieve data from multiple endpoints of the HubSpot API using a specified API key. The retrieved data is returned as a tuple of Dlt resources, one for each endpoint.

The source retrieves data from the following endpoints:
- CRM Companies
- CRM Contacts
- CRM Deals
- CRM Tickets
- CRM Products
- CRM Quotes
- Web Analytics Events

For each endpoint, a resource and transformer function are defined to retrieve data and transform it to a common format.
The resource functions yield the raw data retrieved from the API, while the transformer functions are used to retrieve
additional information from the Web Analytics Events endpoint.

The source also supports enabling Web Analytics Events for each endpoint by setting the corresponding enable flag to True.

"""

import datetime
from collections.abc import Iterator, Sequence
from typing import Any, Literal, Optional
from urllib.parse import quote

import dlt
from dagster._time import get_current_datetime
from dlt.common.typing import TDataItems
from dlt.sources import DltResource

from .helpers import _get_property_names, fetch_data, fetch_property_history
from .settings import (
    ALL,
    CRM_OBJECT_ENDPOINTS,
    DEFAULT_COMPANY_PROPS,
    DEFAULT_DEAL_PROPS,
    DEFAULT_PRODUCT_PROPS,
    DEFAULT_QUOTE_PROPS,
    DEFAULT_TICKET_PROPS,
    OBJECT_TYPE_PLURAL,
    STARTDATE,
    WEB_ANALYTICS_EVENTS_ENDPOINT,
)

THubspotObjectType = Literal["company", "contact", "deal", "ticket", "product", "quote"]


def crm_objects(
    object_type: str,
    api_key: str = dlt.secrets.value,
    include_history: bool = False,
    props: Optional[Sequence[str]] = None,
    include_custom_props: bool = True,
) -> Iterator[TDataItems]:
    """Building blocks for CRM resources."""
    if props == ALL:
        props = list(_get_property_names(api_key, object_type))

    if include_custom_props:
        all_props = _get_property_names(api_key, object_type)
        custom_props = [prop for prop in all_props if not prop.startswith("hs_")]
        props = props + custom_props  # type: ignore

    props = str(",".join(sorted(list(set(props)))))  # type: ignore

    if len(props) > 2000:
        raise ValueError(
            "Your request to Hubspot is too long to process. "
            "Maximum allowed query length is 2000 symbols, while "
            f"your list of properties `{props[:200]}`... is {len(props)} "
            "symbols long. Use the `props` argument of the resource to "
            "set the list of properties to extract from the endpoint."
        )

    params = {"properties": props, "limit": 100}

    yield from fetch_data(CRM_OBJECT_ENDPOINTS[object_type], api_key, params=params)
    if include_history:
        # Get history separately, as requesting both all properties and history together
        # is likely to hit hubspot's URL length limit
        for history_entries in fetch_property_history(
            CRM_OBJECT_ENDPOINTS[object_type],
            api_key,
            props,
        ):
            yield dlt.mark.with_table_name(
                history_entries,
                OBJECT_TYPE_PLURAL[object_type] + "_property_history",
            )


@dlt.source(name="hubspot")
def hubspot(
    api_key: str = dlt.secrets.value,
    include_history: bool = False,
    include_custom_props: bool = False,
) -> Sequence[DltResource]:
    """A DLT source that retrieves data from the HubSpot API using the
    specified API key.

    This function retrieves data for several HubSpot API endpoints,
    including companies, contacts, deals, tickets, products and web
    analytics events. It returns a tuple of Dlt resources, one for
    each endpoint.

    Args:
        api_key (Optional[str]):
            The API key used to authenticate with the HubSpot API. Defaults
            to dlt.secrets.value.
        include_history (Optional[bool]):
            Whether to load history of property changes along with entities.
            The history entries are loaded to separate tables.

    Returns:
        Sequence[DltResource]: Dlt resources, one for each HubSpot API endpoint.

    Notes:
        This function uses the `fetch_data` function to retrieve data from the
        HubSpot CRM API. The API key is passed to `fetch_data` as the
        `api_key` argument.
    """

    @dlt.resource(name="companies", write_disposition="replace")
    def companies(
        api_key: str = api_key,
        include_history: bool = include_history,
        props: Sequence[str] = DEFAULT_COMPANY_PROPS,
        include_custom_props: bool = include_custom_props,
    ) -> Iterator[TDataItems]:
        """Hubspot companies resource."""
        yield from crm_objects(
            "company",
            api_key,
            include_history=include_history,
            props=props,
            include_custom_props=include_custom_props,
        )

    # TODO - this is throwing an exception:
    #
    # <class 'dlt.normalize.exceptions.NormalizeJobFailed'>
    # Job for contacts_property_history.4f26871011.jsonl failed terminally in load 1710521538.008538 with message '_pendulum.Duration' object has no attribute 'year'.

    # @dlt.resource(name="contacts", write_disposition="replace")
    # def contacts(
    #     api_key: str = api_key,
    #     include_history: bool = include_history,
    #     props: Sequence[str] = DEFAULT_CONTACT_PROPS,
    #     include_custom_props: bool = include_custom_props,
    # ) -> Iterator[TDataItems]:
    #     """Hubspot contacts resource."""
    #     yield from crm_objects(
    #         "contact",
    #         api_key,
    #         include_history,
    #         props,
    #         include_custom_props,
    #     )

    @dlt.resource(name="deals", write_disposition="replace")
    def deals(
        api_key: str = api_key,
        include_history: bool = include_history,
        props: Sequence[str] = DEFAULT_DEAL_PROPS,
        include_custom_props: bool = include_custom_props,
    ) -> Iterator[TDataItems]:
        """Hubspot deals resource."""
        yield from crm_objects(
            "deal",
            api_key,
            include_history,
            props,
            include_custom_props,
        )

    @dlt.resource(name="tickets", write_disposition="replace")
    def tickets(
        api_key: str = api_key,
        include_history: bool = include_history,
        props: Sequence[str] = DEFAULT_TICKET_PROPS,
        include_custom_props: bool = include_custom_props,
    ) -> Iterator[TDataItems]:
        """Hubspot tickets resource."""
        yield from crm_objects(
            "ticket",
            api_key,
            include_history,
            props,
            include_custom_props,
        )

    @dlt.resource(name="products", write_disposition="replace")
    def products(
        api_key: str = api_key,
        include_history: bool = include_history,
        props: Sequence[str] = DEFAULT_PRODUCT_PROPS,
        include_custom_props: bool = include_custom_props,
    ) -> Iterator[TDataItems]:
        """Hubspot products resource."""
        yield from crm_objects(
            "product",
            api_key,
            include_history,
            props,
            include_custom_props,
        )

    @dlt.resource(name="quotes", write_disposition="replace")
    def quotes(
        api_key: str = api_key,
        include_history: bool = include_history,
        props: Sequence[str] = DEFAULT_QUOTE_PROPS,
        include_custom_props: bool = include_custom_props,
    ) -> Iterator[TDataItems]:
        """Hubspot quotes resource."""
        yield from crm_objects(
            "quote",
            api_key,
            include_history,
            props,
            include_custom_props,
        )

    # return companies, contacts, deals, tickets, products, quotes
    return companies, deals, tickets, products, quotes


@dlt.resource
def hubspot_events_for_objects(
    object_type: THubspotObjectType,
    object_ids: list[str],
    api_key: str = dlt.secrets.value,
    start_date: datetime.datetime = STARTDATE,
) -> DltResource:
    """A standalone DLT resources that retrieves web analytics events from the HubSpot API for a particular object type and list of object ids.

    Args:
        object_type(THubspotObjectType, required): One of the hubspot object types see definition of THubspotObjectType literal
        object_ids: (List[THubspotObjectType], required): List of object ids to track events
        api_key (str, optional): The API key used to authenticate with the HubSpot API. Defaults to dlt.secrets.value.
        start_date (datetime, optional): The initial date time from which start getting events, default to STARTDATE

    Returns:
        incremental dlt resource to track events for objects from the list
    """
    end_date = get_current_datetime().isoformat()
    name = object_type + "_events"

    def get_web_analytics_events(
        occurred_at: dlt.sources.incremental[str],
    ) -> Iterator[list[dict[str, Any]]]:
        """A helper function that retrieves web analytics events for a given object type from the HubSpot API.

        Args:
            object_type (str): The type of object for which to retrieve web analytics events.

        Yields:
            dict: A dictionary representing a web analytics event.
        """
        for object_id in object_ids:
            yield from fetch_data(
                WEB_ANALYTICS_EVENTS_ENDPOINT.format(
                    objectType=object_type,
                    objectId=object_id,
                    occurredAfter=quote(str(occurred_at.last_value)),
                    occurredBefore=quote(end_date),
                ),
                api_key=api_key,
            )

    return dlt.resource(
        get_web_analytics_events,
        name=name,
        primary_key="id",
        write_disposition="append",
        selected=True,
        table_name=lambda e: name + "_" + str(e["eventType"]),
    )(dlt.sources.incremental("occurredAt", initial_value=start_date.isoformat()))


if __name__ == "__main__":
    dlt_source = (hubspot(include_history=True),)
    dlt_pipeline = dlt.pipeline(
        pipeline_name="hubspot",
        dataset_name="hubspot",
        destination="snowflake",
    )
    dlt_pipeline.run(dlt_source)
