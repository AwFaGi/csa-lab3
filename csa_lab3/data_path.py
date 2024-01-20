import enum

from csa_lab3.isa import MemoryWord


class Register:
    def __init__(self, num_of_bits: int = 8, name: str = "Unknown"):
        self.num_of_bits = num_of_bits  # bits of data
        self.bit_set = 0  # a bit for input
        self.bit_enabled = 0  # a bit for output

        self._value = 0x0

        self.name = name
        self.hex_symbols = num_of_bits // 4 + (0 if num_of_bits % 4 == 0 else 1)

    def open_in(self) -> None:
        self.bit_set = 1

    def close_in(self) -> None:
        self.bit_set = 0

    def open_out(self) -> None:
        self.bit_enabled = 1

    def close_out(self) -> None:
        self.bit_enabled = 0

    def get_bit_set(self) -> int:
        return self.bit_set

    def get_bit_enabled(self) -> int:
        return self.bit_enabled

    def get_value(self) -> int:
        return self._value

    def set_value(self, value: int) -> None:
        assert value >= 0, f"Can't set negative value: {value}"
        self._value = value % (1 << self.num_of_bits)

    def __str__(self) -> str:
        return f'{self.name}: {hex(self._value)[2:].upper().zfill(self.hex_symbols)}'


class Memory:
    def __init__(self, address_register: Register, data_register: Register):
        self.address_register = address_register
        self.data_register = data_register

        self.max_size = 1 << self.address_register.num_of_bits
        self.memory: dict[int, MemoryWord] = {}

    def fill_data(self, data: list[MemoryWord]) -> None:
        for addr, value in enumerate(data, start=0):
            self.memory[addr] = value

    def signal_write(self) -> None:
        self.memory[self.address_register.get_value()] = MemoryWord(self.data_register.get_value())

    def signal_read(self) -> None:
        if self.address_register.get_value() in self.memory:
            self.data_register.set_value(self.memory[self.address_register.get_value()].value)
        else:
            self.data_register.set_value(0)


class Bus:
    def __init__(self) -> None:
        self.value = 0
        self.registers: list[Register] = []

    def add_register(self, register: Register) -> None:
        self.registers.append(register)

    def perform_transfer(self) -> None:
        for register in self.registers:
            if register.bit_enabled == 1:
                self.value = register.get_value()
                break
        else:
            return

        for register in self.registers:
            if register.bit_set == 1:
                register.set_value(self.value)


class AluOperation(enum.Enum):
    ADD = enum.auto()
    SUB = enum.auto()
    MUL = enum.auto()
    DIV = enum.auto()

    AND = enum.auto()
    OR = enum.auto()

    INCL = enum.auto()
    INCR = enum.auto()
    DECL = enum.auto()
    DECR = enum.auto()
    SHL = enum.auto()
    SHR = enum.auto()


class Alu:
    def __init__(self, in_register_left: Register, in_register_right: Register, out_register: Register):
        self.in_register_left = in_register_left
        self.in_register_right = in_register_right
        self.out_register = out_register

        self.bits = self.out_register.num_of_bits

        self.flags = {
            "N": 0,
            "Z": 0,
            "V": 0,
            "C": 0
        }

    def _calculate_complement(self, num: int) -> int:
        return ((num ^ ((1 << self.bits) - 1)) + 1) % (1 << self.bits)

    def perform_operation(self, operation: AluOperation, flags: str = "NZVC") -> None:
        match operation:
            case AluOperation.ADD:
                left = self.in_register_left.get_value()
                right = self.in_register_right.get_value()
                result = left + right + self.flags['C']

                self.out_register.set_value(result)
                self.set_flags(result, left, right, flags=flags)

            case AluOperation.SUB:
                left = self.in_register_left.get_value()
                right = self.in_register_right.get_value()
                result = left + self._calculate_complement(right)

                self.out_register.set_value(result)
                self.set_flags(result, left, right, flags=flags)

            case AluOperation.AND:
                left = self.in_register_left.get_value()
                right = self.in_register_right.get_value()
                result = left & right

                self.out_register.set_value(result)
                self.set_flags(result, left, right, flags=flags)

            case AluOperation.OR:
                left = self.in_register_left.get_value()
                right = self.in_register_right.get_value()
                result = left | right

                self.out_register.set_value(result)
                self.set_flags(result, left, right, flags=flags)

            case AluOperation.INCL:
                left = self.in_register_left.get_value()
                right = self.in_register_right.get_value()
                result = left + 1

                self.out_register.set_value(result)
                self.set_flags(result, left, right, flags="NZV")

            case AluOperation.INCR:
                left = self.in_register_left.get_value()
                right = self.in_register_right.get_value()
                result = right + 1

                self.out_register.set_value(result)
                self.set_flags(result, left, right, flags="NZV")

            case AluOperation.DECL:
                left = self.in_register_left.get_value()
                right = self.in_register_right.get_value()
                result = left + self._calculate_complement(1)

                self.out_register.set_value(result)
                self.set_flags(result, left, right, flags="NZV")

            case AluOperation.DECR:
                left = self.in_register_left.get_value()
                right = self.in_register_right.get_value()
                result = right + self._calculate_complement(1)

                self.out_register.set_value(result)
                self.set_flags(result, left, right, flags="NZV")

            case AluOperation.SHL:
                left = self.in_register_left.get_value()
                right = self.in_register_right.get_value()
                result = left << right

                self.out_register.set_value(result)
                self.set_flags(result, left, right, flags="C")

            case AluOperation.SHR:
                left = self.in_register_left.get_value()
                right = self.in_register_right.get_value()
                result = left >> right

                self.out_register.set_value(result)
                self.set_flags(result, left, right, flags="C")

    def set_flags(self, result: int, left: int, right: int, flags: str = "NZVC") -> None:
        if 'N' in flags:
            self.flags['N'] = int(result & (1 << (self.bits - 1)) != 0)
        if 'Z' in flags:
            self.flags['Z'] = int((result % (1 << self.bits)) == 0)
        if 'V' in flags:
            l_bit = left & (1 << (self.bits - 1))
            r_bit = right & (1 << (self.bits - 1))
            o_bit = result & (1 << (self.bits - 1))
            if l_bit == r_bit and l_bit != o_bit:
                self.flags['V'] = 1
            else:
                self.flags['V'] = 0
        if 'C' in flags:
            self.flags['C'] = int(result > (1 << self.bits))

    def flags_str(self) -> str:
        return ", ".join([f'{i}: {j}' for i, j in self.flags.items()])


class IoDevice:
    def __init__(self, register: Register):
        self.register = register

    def after_perform_action(self) -> None:
        raise NotImplementedError


class StdIn(IoDevice):
    def __init__(self, register: Register, buffer: list[str]):
        super().__init__(register)
        self.buffer = buffer
        self.counter = 0
        self.after_perform_action()

    def after_perform_action(self) -> None:
        if self.counter >= len(self.buffer):
            self.register.set_value(0)
            return
        self.register.set_value(ord(self.buffer[self.counter]))
        self.counter += 1


class StdOut(IoDevice):
    def __init__(self, register: Register):
        super().__init__(register)
        self.buffer: list[str] = []

    def after_perform_action(self) -> None:
        self.buffer.append(chr(self.register.get_value()))


class DataPath:
    def __init__(self, in_buffer: list[str]) -> None:
        self.AC = Register(name='AC')  # accumulator
        self.BR = Register(name='BR')  # buffer

        self.INL = Register(name='INL')  # ALU left in
        self.INR = Register(name='INR')  # ALU right in
        self.OUT = Register(name='OUT')  # ALU out

        self.DR = Register(name='DR')  # data register
        self.DP = Register(name='DP')  # data pointer

        self.R0 = Register(name='R0')  # common register 0

        self.IOR = Register(name='IOR')  # I/O data

        self.data_bus = Bus()
        self.data_bus.add_register(self.OUT)
        self.data_bus.add_register(self.AC)
        self.data_bus.add_register(self.BR)
        self.data_bus.add_register(self.R0)
        self.data_bus.add_register(self.DR)
        self.data_bus.add_register(self.DP)
        self.data_bus.add_register(self.IOR)
        self.data_bus.add_register(self.INL)
        self.data_bus.add_register(self.INR)

        self.data_memory = Memory(data_register=self.DR, address_register=self.DP)

        self.alu = Alu(in_register_left=self.INL, in_register_right=self.INR, out_register=self.OUT)

        self.stdin = StdIn(Register(name="stdin"), in_buffer)
        self.stdout = StdOut(Register(name="stdout"))

        self.ports = {
            0: self.stdin,
            1: self.stdout
        }
