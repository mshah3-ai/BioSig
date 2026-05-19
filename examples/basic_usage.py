from biosig import BiosigReader
from biosig.convert import convert_edf_to_bsg

convert_edf_to_bsg("example.rec", "example.bsg")

with BiosigReader("example.bsg") as reader:
    print(reader.header)
    window = reader.read_seconds(channel=0, start=30, end=90)
    print(window.shape)
