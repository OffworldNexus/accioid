Feature: Turning the Telperion switch off into an action
  As the Accioid core
  I want a switch left off to become an action
  So that the read API and the card have something real to show

  Scenario: Off creates an action, on closes it, off again creates a new one
    Given Accioid is set up with the Telperion switch off
    Then an open action titled "Turn on Telperion" exists
    When the Telperion switch is turned on
    Then there are no open actions
    When the Telperion switch is turned off
    Then an open action titled "Turn on Telperion" exists
    And the new action has a different id
