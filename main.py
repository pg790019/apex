"""Main program to multiply two integers."""
from typing import Tuple

def multiply(a: int, b: int) -> int:
    """Return the product of two integers."""
    return a * b


def main() -> None:
    # Demonstrate multiplication with sample inputs
    result = multiply(3, 4)
    print(f"3 multiplied by 4 is {result}")


if __name__ == "__main__":
    main()