import unittest

from cherryctl import protocol


class PacketTest(unittest.TestCase):
    def test_read_request(self):
        self.assertEqual(protocol.read_request(5, 1, 0x16).hex(" "), "04 1c 00 05 01 16 00 00")

    def test_write_request(self):
        self.assertEqual(protocol.write_request(6, b"\x02", 0x16).hex(" "), "04 1f 00 06 01 16 00 00 02")

    def test_checksum_carries_into_high_byte(self):
        record = protocol.haptics_preset("round", 17, 40, 14, -3, False, 6)
        packet = protocol.write_request(0x7D, record, 0)
        self.assertEqual(packet.hex(" "), "04 d0 01 7d 07 00 00 00 02 11 28 0e fd 00 06")

    def test_pad(self):
        padded = protocol.pad(protocol.read_request(5, 1, 0x16))
        self.assertEqual(len(padded), 64)
        self.assertEqual(padded[8:], bytes(56))

    def test_parse_reply(self):
        request = protocol.read_request(5, 1, 0x17)
        reply = bytes.fromhex("04 20 00 05 01 17 00 00 03") + bytes(55)
        self.assertEqual(protocol.parse_reply(request, reply), b"\x03")

    def test_parse_reply_rejects_other_offset(self):
        request = protocol.read_request(5, 1, 0x17)
        reply = bytes.fromhex("04 1f 00 05 01 16 00 00 03") + bytes(55)
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse_reply(request, reply)


    def test_parse_reply_rejects_bad_checksum(self):
        request = protocol.read_request(5, 1, 0x17)
        reply = bytes.fromhex("04 21 00 05 01 17 00 00 03") + bytes(55)
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse_reply(request, reply)


class EncodingTest(unittest.TestCase):
    def test_dpi(self):
        self.assertEqual([protocol.encode_dpi(d) for d in (200, 1000, 6000)], [1, 9, 59])

    def test_dpi_rejects_out_of_range(self):
        for dpi in (100, 6100, 850):
            with self.assertRaises(ValueError):
                protocol.encode_dpi(dpi)

    def test_dpi_table(self):
        self.assertEqual(protocol.dpi_table([1000, 2000, 3000, 4000]).hex(" "), "09 00 13 00 1d 00 27 00")

    def test_haptics_range(self):
        with self.assertRaises(ValueError):
            protocol.haptics_preset("sharp", 37, 40, 14, 0, False, 6)


if __name__ == "__main__":
    unittest.main()
