provider "aws" {
  region = "ap-south-1"
}

resource "aws_instance" "mumbai_ec2" {
  ami = "ami-0abcdef1234567890"
  instance_type = "t2.micro"
  tags = {
    Name = "MumbaiEC2"
  }
}
