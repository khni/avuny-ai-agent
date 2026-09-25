from datetime import date


def calculate_age(birthday):
    """Calculate age in years from a birthday (date object)."""
    today = date.today()
    years = today.year - birthday.year
    if (today.month, today.day) < (birthday.month, birthday.day):
        years -= 1
    return years


def parse_birthday(text):
    """Parse a birthday string in YYYY-MM-DD format."""
    return date.fromisoformat(text)


if __name__ == "__main__":
    birthday_input = input("Enter your birthday (YYYY-MM-DD): ")
    birthday = parse_birthday(birthday_input)
    print(f"You are {calculate_age(birthday)} years old.")
