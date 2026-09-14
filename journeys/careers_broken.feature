Feature: Careers page
  Scenario: Jobs board is published
    Given I open the home page
    When I click "Careers"
    Then I should see "Join our team"
