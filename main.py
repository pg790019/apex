# Main implementation of the program

def generate_multiples_of_two():
    return [i for i in range(1, 201) if i % 2 == 0]

if __name__ == "__main__":
    print(generate_multiples_of_two())
