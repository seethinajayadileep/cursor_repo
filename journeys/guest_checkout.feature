Feature: Guest checkout
  Scenario: Buy the red mug
    Given I open the home page
    When I click "Shop"
    And I click "Red Mug"
    And I click "Add to cart"
    And I fill "Full name" with "Ada Lovelace"
    And I fill "Email" with "ada@example.com"
    And I click "Place order"
    Then I should see "Order confirmed"
    And the url should contain "/checkout"
