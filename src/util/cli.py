"""Command line interface utilities."""

import datetime
import logging

logger = logging.getLogger(__name__)


def prompt_selection(options, prompt="Select an option:"):
    """Prompt the user to select an option from a list of options.

    The user's selection is returned as an index.
    """
    selection = None
    while selection is None:
        print("\n#####################################")
        print(prompt)
        for i, option in enumerate(options):
            print(f"{i + 1}). {option}")
        print()

        try:
            selection = int(input())
        except ValueError:
            logger.error("Invalid selection. Please enter valid number from the list.")

    return selection - 1


def prompt_yes_no(prompt="Do you want to continue? "):
    """Prompt the user to select a boolean value."""

    selection = input(f"{prompt} (y/N): ")

    return selection.lower() in ["y", "yes"]


def prompt_date(default, prompt="Enter a date"):
    """Prompt the user to enter a date."""
    date_input = input(f"{prompt} ({default}):")

    if not date_input:
        return default

    return (
        datetime.datetime.fromisoformat(date_input).isoformat(timespec="seconds") + "Z"
    )


def select_named_item(items, prompt):
    """Prompt the user to select an item from a list of items."""
    try:
        item_names = [item["name"] for item in items]
    except KeyError:
        logger.error("Items must have a 'name' key.")
    selected_item_index = prompt_selection(item_names, prompt)
    return items[selected_item_index]
