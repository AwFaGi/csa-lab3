import pytest
from csa_lab3.data_path import Alu, Register, AluOperation


@pytest.fixture()
def get_alu():
    inl = Register()
    inr = Register()
    out = Register()
    alu = Alu(inl, inr, out)

    return alu


class TestAlu:

    def test__calculate_complement(self, get_alu):
        assert get_alu._calculate_complement(0) == 0
        assert get_alu._calculate_complement(1) == 255
        assert get_alu._calculate_complement(-1) == 1

    def test_perform_operation(self, get_alu):
        alu = get_alu

        alu.in_register_left.set_value(2)
        alu.in_register_right.set_value(3)
        alu.perform_operation(AluOperation.ADD)
        assert alu.out_register.get_value() == 5

        alu.in_register_left.set_value(2)
        alu.in_register_right.set_value(3)
        alu.perform_operation(AluOperation.SUB)
        assert alu.out_register.get_value() == alu._calculate_complement(1)

        alu.in_register_left.set_value(1)
        alu.in_register_right.set_value(4)
        alu.perform_operation(AluOperation.SHL)
        assert alu.out_register.get_value() == 16

        alu.in_register_left.set_value(32)
        alu.in_register_right.set_value(4)
        alu.perform_operation(AluOperation.SHR)
        assert alu.out_register.get_value() == 2

    def test_flags_str(self, get_alu):
        get_alu.flags["N"] = 0
        get_alu.flags["Z"] = 1
        get_alu.flags["V"] = 0
        get_alu.flags["C"] = 1

        assert get_alu.flags_str() == "N: 0, Z: 1, V: 0, C: 1"

    def test_set_flags(self, get_alu):
        alu = get_alu
        alu.in_register_left.set_value(2)
        alu.in_register_right.set_value(3)
        alu.perform_operation(AluOperation.SUB)

        assert alu.flags_str() == "N: 1, Z: 0, V: 1, C: 0"
