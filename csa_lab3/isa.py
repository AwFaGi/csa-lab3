from __future__ import annotations
from dataclasses import dataclass, field
import enum


class OperandAddress(enum.Enum):
    NO_ADDRESS = 0x0
    MEMORY_DIRECT = 0x1
    DIRECT_LOAD = 0x2
    REGISTER = 0x3

    @staticmethod
    def from_hex(value: int) -> OperandAddress:
        for c in OperandAddress:
            if c.value == value:
                return c
        raise ValueError


class CommandName(enum.Enum):
    NOP = 0x0
    HLT = 0x1

    INC = 0x2
    DEC = 0x3

    LD = 0x4
    ST = 0x5

    OR = 0x6
    AND = 0x7

    SHL = 0x8
    SHR = 0x9

    ADD = 0xA
    SUB = 0xB

    MUL = 0xC
    DIV = 0xD

    ADD1 = 0xE
    SUB1 = 0xF

    CMP = 0x10
    JMP = 0x11

    JE = 0x12
    JNE = 0x13

    JA = 0x14
    JAE = 0x15

    JB = 0x16
    JBE = 0x17

    MOV = 0x20
    MOV4 = 0x21

    IN = 0x22
    OUT = 0x23

    @staticmethod
    def from_hex(value: int) -> CommandName:
        for c in CommandName:
            if c.value == value:
                return c
        raise ValueError


@dataclass
class Operand:
    address: OperandAddress
    value: int

    def __str__(self) -> str:
        match self.address:
            case OperandAddress.MEMORY_DIRECT:
                return f'${hex(self.value)[2:].zfill(2)}'
            case OperandAddress.REGISTER:
                return f'R{hex(self.value)[2:].zfill(2)}'
            case OperandAddress.DIRECT_LOAD:
                return f'.{hex(self.value)[2:].zfill(2)}'
            case _:
                return '--'

    def __repr__(self) -> str:
        return bin(self.value)[2:].zfill(8)


@dataclass
class Command:
    name: CommandName
    operands: list[Operand] = field(default_factory=lambda: [])
    address: int = 0

    def get_addr(self) -> str:
        return hex(self.address)[2:].zfill(2)

    def __str__(self) -> str:
        match self.operands:
            case [a]:
                return f'{self.name.name} {str(a)}'
            case [a, b]:
                return f'{self.name.name} {str(a)}, {str(b)}'
            case [a, b, c]:
                return f'{self.name.name} {str(a)} <- {str(b)}, {str(c)}'
            case _:
                return f'{self.name.name}'

    def __repr__(self) -> str:
        if len(self.operands) == 0:
            return f'{bin(self.address)[2:].zfill(8)}{bin(self.name.value)[2:].zfill(8)}'

        addresses = "".join([bin(o.address.value)[2:].zfill(2) for o in self.operands]).ljust(8, '0')
        ops = "".join([bin(o.value)[2:].zfill(8) for o in self.operands])

        return f"{bin(self.address)[2:].zfill(8)}{bin(self.name.value)[2:].zfill(8)}{addresses}{ops}"


@dataclass
class MemoryWord:
    value: int

    def __str__(self) -> str:
        return hex(self.value)[2:].zfill(2)


def write_commands(commands: list[Command], memory: list[MemoryWord], filename: str) -> None:
    def splitter(s: str) -> list[str]:
        return [s[0 + i * 8: 8 + i * 8] for i in range(len(s) // 8)]

    with open(filename, 'wb') as bin_file:
        for cmd in commands:
            for byte in splitter(repr(cmd)):
                bin_file.write(int(byte, 2).to_bytes(1, 'big'))

    with open(f'{filename}.mem', 'wb') as mem_file:
        for mw in memory:
            mem_file.write(int(mw.value).to_bytes(1, 'big'))

    with open(f'{filename}.txt', 'w', encoding="utf-8") as readable_file:
        for cmd in commands:
            readable_file.write(f"{cmd.get_addr()} | {repr(cmd).ljust(6 * 8)} | {str(cmd)}\n")


def read_commands(filename: str) -> list[Command]:
    with open(filename, 'rb') as file:
        data = file.read()

    commands = []

    counter = 0
    while counter < len(data):
        command_addr = int.from_bytes(bytes([data[counter]]), byteorder='big')

        counter += 1
        if counter >= len(data):
            break

        command_name = int.from_bytes(bytes([data[counter]]), byteorder='big')
        cmd_name = CommandName.from_hex(command_name)

        cmd = Command(cmd_name)
        cmd.address = command_addr
        commands.append(cmd)

        counter += 1
        if cmd_name in [CommandName.HLT, CommandName.NOP]:
            continue

        if counter >= len(data):
            break

        addresses = bin(int.from_bytes(bytes([data[counter]]), byteorder='big'))[2:].zfill(8)

        op_addr_1 = OperandAddress.from_hex(int(addresses[0:2], 2))
        op_addr_2 = OperandAddress.from_hex(int(addresses[2:4], 2))
        op_addr_3 = OperandAddress.from_hex(int(addresses[4:6], 2))
        op_addr_4 = OperandAddress.from_hex(int(addresses[6:8], 2))

        counter += 1

        if op_addr_1 != OperandAddress.NO_ADDRESS:
            value = int.from_bytes(bytes([data[counter]]), byteorder='big')
            cmd.operands.append(Operand(op_addr_1, value))
        else:
            continue

        counter += 1

        if op_addr_2 != OperandAddress.NO_ADDRESS:
            value = int.from_bytes(bytes([data[counter]]), byteorder='big')
            cmd.operands.append(Operand(op_addr_2, value))
        else:
            continue

        counter += 1

        if op_addr_3 != OperandAddress.NO_ADDRESS:
            value = int.from_bytes(bytes([data[counter]]), byteorder='big')
            cmd.operands.append(Operand(op_addr_3, value))
        else:
            continue

        counter += 1

        if op_addr_4 != OperandAddress.NO_ADDRESS:
            value = int.from_bytes(bytes([data[counter]]), byteorder='big')
            cmd.operands.append(Operand(op_addr_4, value))
        else:
            continue

        counter += 1

    return commands


def read_memory(filename: str) -> list[MemoryWord]:
    with open(filename, 'rb') as file:
        data = file.read()

    memory = []

    counter = 0
    while counter < len(data):
        memory.append(MemoryWord(int.from_bytes(bytes([data[counter]]), byteorder='big')))
        counter += 1

    return memory
