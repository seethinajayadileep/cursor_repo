from __future__ import annotations

from openscout.matcher import find_element, score_element
from openscout.models import Element, Snapshot
from openscout.planner import parse_journey, parse_step


def test_parse_gherkin_checkout() -> None:
    text = """
    Feature: Guest checkout
      Scenario: Buy the red mug
        Given I open the home page
        When I click "Shop"
        And I fill "Email" with "ada@example.com"
        Then I should see "Order confirmed"
        And the url should contain "/checkout"
    """
    journey = parse_journey(text)
    types = [step.type for step in journey.steps]
    assert journey.name == "Buy the red mug"
    assert types == ["open", "click", "fill", "see", "url_contains"]
    assert journey.steps[2].value == "ada@example.com"


def test_parse_type_into() -> None:
    action = parse_step('I type "Ada Lovelace" into "Full name"')
    assert action is not None
    assert action.type == "fill"
    assert action.target == "Full name"
    assert action.value == "Ada Lovelace"


def test_parse_no_console_and_wait() -> None:
    assert parse_step("Then the page should have no console errors").type == "no_console"
    wait = parse_step("And I wait 250 ms")
    assert wait.type == "wait"
    assert wait.value == "250"


def test_click_prefers_button_named_place_order() -> None:
    snapshot = Snapshot(
        url="http://x/cart",
        title="Cart",
        text="Cart",
        elements=[
            Element(id=0, tag="button", type="button", text="Express checkout", label="Express checkout"),
            Element(id=1, tag="button", type="submit", text="Place order", label="Place order"),
            Element(id=2, tag="input", type="email", name="email", label="Email", placeholder="you@shop.com"),
        ],
    )
    found = find_element(snapshot, "Place order", "click")
    assert found is not None
    assert found.id == 1
    assert score_element("Email", snapshot.elements[2], "fill") > 0.9
