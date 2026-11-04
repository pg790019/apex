def subtract(a: int, b: int):
    """Return the difference of two integers."""
    return a - b


def main():
    # Demonstrate the subtract function with sample inputs
    print(f"Subtracting 5 - 3 gives {subtract(5, 3)}")
    print(f"Subtracting 0 - 0 gives {subtract(0, 0)}")
    print(f"Subtracting -4 - (-6) gives {subtract(-4, -6)}")


if __name__ == "__main__":
    main()