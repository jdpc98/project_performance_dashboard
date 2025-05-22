from app_main import parse_contract
from print_utils import print_green, print_orange, print_red

print_green("Testing contract amount parsing")
test_values = [
    None,
    '',
    ' ',
    '$1,000.00',
    '1000',
    1000,
    0
]

for val in test_values:
    result = parse_contract(val)
    print_green(f"Parsing {val!r} gives {result!r}")
