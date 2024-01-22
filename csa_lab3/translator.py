from __future__ import annotations

import enum
import io
import sys
from typing import Any, Tuple

from csa_lab3.isa import Command, MemoryWord, CommandName, Operand, OperandAddress, write_commands


class LanguagePart(enum.Enum):
    NUMBER = enum.auto()
    STRING = enum.auto()
    CHAR = enum.auto()

    VARIABLE = enum.auto()

    WHILE = enum.auto()

    IF = enum.auto()

    PLUS = enum.auto()
    MINUS = enum.auto()
    MULTIPLICATION = enum.auto()
    DIVISION = enum.auto()
    MOD = enum.auto()

    EQUALS = enum.auto()
    NOT_EQUALS = enum.auto()
    LESS = enum.auto()
    GREATER = enum.auto()
    LESS_OR_EQUALS = enum.auto()
    GREATER_OR_EQUALS = enum.auto()

    PRINT_CALL = enum.auto()
    READ_CALL = enum.auto()

    ASSIGN = enum.auto()
    SEMICOLON = enum.auto()

    L_BRA = enum.auto()
    R_BRA = enum.auto()

    L_PAR = enum.auto()
    R_PAR = enum.auto()

    QUOTE = enum.auto()
    SINGLE_QUOTE = enum.auto()

    EOF = enum.auto()


class Lexer:
    SYMBOLS = {
        '{': LanguagePart.L_BRA,
        '}': LanguagePart.R_BRA,
        '(': LanguagePart.L_PAR,
        ')': LanguagePart.R_PAR,
        ';': LanguagePart.SEMICOLON,
        '=': LanguagePart.ASSIGN,
        '+': LanguagePart.PLUS,
        '-': LanguagePart.MINUS,
        '*': LanguagePart.MULTIPLICATION,
        '/': LanguagePart.DIVISION,
        '%': LanguagePart.MOD,
        '<': LanguagePart.LESS,
        '>': LanguagePart.GREATER,
        '==': LanguagePart.EQUALS,
        '!=': LanguagePart.NOT_EQUALS,
        '<=': LanguagePart.LESS_OR_EQUALS,
        '>=': LanguagePart.GREATER_OR_EQUALS
    }

    WORDS = {
        'if': LanguagePart.IF,
        'while': LanguagePart.WHILE,
        'print': LanguagePart.PRINT_CALL,
        'read': LanguagePart.READ_CALL
    }

    def __init__(self, program: str):
        self.buffer = io.StringIO(program)
        self.current_char: str = ' '

    def read_char(self) -> None:
        self.current_char = self.buffer.read(1)

    def parse_token(self) -> Tuple[LanguagePart, Any]:
        value: Any = None
        while True:
            if len(self.current_char) == 0:
                return LanguagePart.EOF, None

            if self.current_char.isspace():
                self.read_char()
                continue

            if self.current_char.isdigit():
                value = 0
                while self.current_char.isdigit():
                    value = value * 10 + int(self.current_char)
                    self.read_char()
                return LanguagePart.NUMBER, value

            if self.current_char == '"':
                value = ''
                self.read_char()
                while self.current_char != '"':
                    value = value + self.current_char
                    self.read_char()
                self.read_char()
                return LanguagePart.STRING, value

            if self.current_char == "'":
                value = ''
                self.read_char()
                while self.current_char != "'":
                    value = value + self.current_char
                    self.read_char()
                self.read_char()
                return LanguagePart.CHAR, value

            if self.current_char.isalpha():
                value = ''
                while self.current_char.isalpha() or self.current_char == '_':
                    value = value + self.current_char
                    self.read_char()

                if value in Lexer.WORDS:
                    return Lexer.WORDS[value], None

                return LanguagePart.VARIABLE, value

            value = self.current_char
            self.read_char()
            next_value = self.current_char

            if value + next_value in Lexer.SYMBOLS:
                self.read_char()
                return Lexer.SYMBOLS[value + next_value], None

            if value in Lexer.SYMBOLS:
                return Lexer.SYMBOLS[value], None

            raise SyntaxError(f"Unexpected token: {value}")


class NodeType(enum.Enum):
    PROGRAM = enum.auto()
    EXPRESSION = enum.auto()
    SEQUENCE = enum.auto()
    EMPTY = enum.auto()

    SET = enum.auto()
    VARIABLE = enum.auto()
    INT_CONST = enum.auto()
    CHAR_CONST = enum.auto()
    STRING_CONST = enum.auto()

    ADD = enum.auto()
    SUB = enum.auto()
    MUL = enum.auto()
    DIV = enum.auto()
    MOD = enum.auto()

    IF = enum.auto()
    IF_ELSE = enum.auto()

    WHILE = enum.auto()

    LESS = enum.auto()
    GREATER = enum.auto()
    EQUALS = enum.auto()
    NOT_EQUALS = enum.auto()
    LESS_OR_EQUALS = enum.auto()
    GREATER_OR_EQUALS = enum.auto()

    PRINT = enum.auto()
    READ = enum.auto()


class AstNode:
    def __init__(self,
                 node_type: NodeType,
                 value: Any = None,
                 op1: AstNode | None = None,
                 op2: AstNode | None = None
                 ) -> None:
        self.node_type: NodeType = node_type
        self.value: Any = value
        self.op1 = op1
        self.op2 = op2

    def __str__(self) -> str:
        if self.value is not None:
            return f"{self.node_type} = {self.value}"

        return f"{self.node_type}"


def pretty_print_ast_node(node: AstNode, shift: str = '') -> None:
    print(f"{shift}{node}")
    if node.op1:
        pretty_print_ast_node(node.op1, shift=shift + "  ")
    if node.op2:
        pretty_print_ast_node(node.op2, shift=shift + "  ")


class Parser:
    math_language_part_to_node_type_map = {
        LanguagePart.PLUS: NodeType.ADD,
        LanguagePart.MINUS: NodeType.SUB,
        LanguagePart.MULTIPLICATION: NodeType.MUL,
        LanguagePart.DIVISION: NodeType.DIV,
        LanguagePart.MOD: NodeType.MOD
    }

    cmp_language_part_to_node_type_map = {
        LanguagePart.LESS: NodeType.LESS,
        LanguagePart.GREATER: NodeType.GREATER,
        LanguagePart.LESS_OR_EQUALS: NodeType.LESS_OR_EQUALS,
        LanguagePart.GREATER_OR_EQUALS: NodeType.GREATER_OR_EQUALS,
        LanguagePart.EQUALS: NodeType.EQUALS,
        LanguagePart.NOT_EQUALS: NodeType.NOT_EQUALS
    }

    def __init__(self, lexer: Lexer) -> None:
        self.lexer = lexer
        self.token: LanguagePart | None = None
        self.value: Any = None

    @staticmethod
    def print_error(msg: str) -> None:
        print(f'Parser error: {msg}')
        raise SystemExit

    def next_token(self) -> None:
        self.token, self.value = self.lexer.parse_token()

    def parse(self) -> AstNode:
        self.next_token()
        node = AstNode(NodeType.PROGRAM, op1=self.statement())

        if self.token != LanguagePart.EOF:
            self.print_error("Invalid statement syntax")

        return node

    def statement(self) -> AstNode:
        match self.token:
            case LanguagePart.IF:
                node = AstNode(NodeType.IF)
                self.next_token()

                node.op1 = self.paren_expression()
                node.op2 = self.statement()

                return node

            case LanguagePart.WHILE:
                node = AstNode(NodeType.WHILE)
                self.next_token()
                node.op1 = self.paren_expression()
                node.op2 = self.statement()

                return node

            case LanguagePart.SEMICOLON:
                node = AstNode(NodeType.EMPTY)
                self.next_token()
                return node

            case LanguagePart.L_BRA:
                node = AstNode(NodeType.EMPTY)
                self.next_token()
                while self.token != LanguagePart.R_BRA:  # type: ignore[comparison-overlap]
                    node = AstNode(NodeType.SEQUENCE, op1=node, op2=self.statement())
                self.next_token()
                return node

            case _:
                node = AstNode(NodeType.EXPRESSION, op1=self.expression())
                if self.token != LanguagePart.SEMICOLON:  # type: ignore[comparison-overlap]
                    self.print_error('";" expected')
                self.next_token()
                return node

    def paren_expression(self) -> AstNode:
        if self.token != LanguagePart.L_PAR:
            self.print_error('"(" expected')
        self.next_token()

        node = self.cmp()

        if self.token != LanguagePart.R_PAR:
            self.print_error('")" expected')
        self.next_token()

        return node

    def expression(self) -> AstNode:
        if self.token == LanguagePart.PRINT_CALL:
            self.next_token()
            return AstNode(NodeType.PRINT, op1=self.term())

        if self.token == LanguagePart.READ_CALL:
            self.next_token()
            return AstNode(NodeType.READ, op1=self.term())

        if self.token != LanguagePart.VARIABLE:
            return self.math()

        node = AstNode(NodeType.SET, op1=AstNode(NodeType.VARIABLE, value=self.value))
        self.next_token()

        if self.token != LanguagePart.ASSIGN:  # type: ignore[comparison-overlap]
            self.print_error('"=" expected')
        self.next_token()

        node.op2 = self.math()

        return node

    def cmp(self) -> AstNode:
        node_1 = self.term()

        if self.token in self.cmp_language_part_to_node_type_map:
            kind = self.cmp_language_part_to_node_type_map[self.token]
            self.next_token()
            return AstNode(kind, op1=node_1, op2=self.term())

        return node_1

    def math(self) -> AstNode:
        node_1 = self.term()

        if self.token in self.math_language_part_to_node_type_map:
            kind = self.math_language_part_to_node_type_map[self.token]
            self.next_token()
            return AstNode(kind, op1=node_1, op2=self.term())

        return node_1

    def term(self) -> AstNode:

        match self.token:
            case LanguagePart.VARIABLE:
                t = NodeType.VARIABLE

            case LanguagePart.NUMBER:
                t = NodeType.INT_CONST

            case LanguagePart.STRING:
                t = NodeType.STRING_CONST

            case LanguagePart.CHAR:
                t = NodeType.CHAR_CONST

            case _:
                raise ValueError(f"Unknown term: {self.token}")

        n = AstNode(t, self.value)
        self.next_token()
        return n


class Compiler:
    math_node_type_to_command_map = {
        NodeType.ADD: CommandName.ADD,
        NodeType.SUB: CommandName.SUB,
        NodeType.MUL: CommandName.MUL,
        NodeType.DIV: CommandName.DIV,
    }

    cmp_node_type_to_command_map = {
        NodeType.LESS: CommandName.JB,
        NodeType.GREATER: CommandName.JA,
        NodeType.EQUALS: CommandName.JE,
        NodeType.NOT_EQUALS: CommandName.JNE,
        NodeType.LESS_OR_EQUALS: CommandName.JBE,
        NodeType.GREATER_OR_EQUALS: CommandName.JAE,
    }

    def __init__(self) -> None:
        self.commands: list[Command] = []
        self.memory: list[MemoryWord] = []

        self.command_counter = 0
        self.memory_counter = 0

        self.variables_address: dict[str, int] = {}
        self.variables_type: dict[str, str] = {}

        self.strings: dict[str, int] = {}
        self.string_dependent: list[tuple[Operand, str]] = []

    def add_command(self, command: Command) -> None:
        command.address = self.command_counter
        self.commands.append(command)
        self.command_counter += 1

        if len(command.operands) != 0:
            self.command_counter += 1
            self.command_counter += len(command.operands)

    def add_memory_word(self, word: list[MemoryWord]) -> int:
        cash = self.memory_counter
        for w in word:
            self.memory.append(w)
            self.memory_counter += 1
        return cash

    @staticmethod
    def split_int(i: int) -> list[int]:
        c = bin(i)[2:].zfill(32)
        return list(reversed((int(c[0:8], 2), int(c[8:16], 2), int(c[16:24], 2), int(c[24:32], 2))))

    def precompile_node(self, node: AstNode | None) -> Operand:
        if node is None:
            raise ValueError

        if node.node_type == NodeType.VARIABLE:
            var = node.value
            if var in self.variables_address:
                addr = self.variables_address[var]
            else:
                addr = self.add_memory_word([MemoryWord(i) for i in self.split_int(0)])
                self.variables_address[var] = addr

            return Operand(OperandAddress.MEMORY_DIRECT, addr)

        if node.node_type == NodeType.INT_CONST:
            if node.value < 256:
                return Operand(OperandAddress.DIRECT_LOAD, node.value)

            addr = self.add_memory_word([MemoryWord(i) for i in self.split_int(node.value)])
            return Operand(OperandAddress.MEMORY_DIRECT, addr)

        if node.node_type == NodeType.CHAR_CONST:

            node.value = node.value.replace(r"\0", '\0')

            if len(node.value) != 1:
                raise ValueError(f'Cannot convert char of len {len(node.value)}: {node.value}')

            addr = self.add_memory_word([MemoryWord(i) for i in self.split_int(ord(node.value))])
            return Operand(OperandAddress.MEMORY_DIRECT, addr)

        if node.node_type == NodeType.STRING_CONST:
            operand = Operand(OperandAddress.DIRECT_LOAD, 0)
            self.string_dependent.append((operand, node.value))
            return operand

        raise ValueError

    def precompile_nodes(self, node: AstNode | None) -> Tuple[Operand, Operand]:
        if node is None:
            raise ValueError

        if node.node_type in Compiler.math_node_type_to_command_map:
            return self.precompile_node(node.op1), self.precompile_node(node.op2)

        if node.node_type in Compiler.cmp_node_type_to_command_map:
            return self.precompile_node(node.op1), self.precompile_node(node.op2)

        raise ValueError

    def compile_node(self, node: AstNode | None) -> None:
        if node is None:
            raise ValueError

        match node.node_type:
            case NodeType.PROGRAM:
                self.compile_node(node.op1)
                self.add_command(Command(CommandName.HLT))

                for op, s in self.string_dependent:
                    s = s.replace(r"\n", '\n')
                    addr = self.add_memory_word([MemoryWord(ord(i)) for i in s] + [MemoryWord(0)])
                    op.value = addr

            case NodeType.SEQUENCE:
                self.compile_node(node.op1)
                self.compile_node(node.op2)

            case NodeType.EMPTY:
                pass

            case NodeType.EXPRESSION:
                self.compile_node(node.op1)

            case NodeType.SET:
                if node.op1 is None:
                    raise ValueError

                op1 = self.precompile_node(node.op1)
                value = node.op2

                if value is None:
                    raise ValueError

                match value.node_type:
                    case NodeType.INT_CONST:

                        self.variables_type[node.op1.value] = "int"

                        op2 = self.precompile_node(value)

                        self.add_command(Command(CommandName.MOV4, [op1, op2]))

                    case NodeType.CHAR_CONST:

                        self.variables_type[node.op1.value] = "char"

                        op2 = self.precompile_node(value)

                        self.add_command(Command(CommandName.MOV, [op1, op2]))

                    case NodeType.VARIABLE:

                        if value.value not in self.variables_type:
                            raise ValueError(f'Unknown variable: {value.value}')

                        if node.op1.value not in self.variables_type:
                            self.variables_type[node.op1.value] = self.variables_type[value.value]

                        op2 = self.precompile_node(value)

                        self.add_command(Command(CommandName.MOV4, [op1, op2]))

                    case _ if value.node_type in Compiler.math_node_type_to_command_map:
                        op2, op3 = self.precompile_nodes(value)

                        self.add_command(
                            Command(Compiler.math_node_type_to_command_map[value.node_type], [op1, op2, op3])
                        )

            case NodeType.WHILE:
                loop_start = self.command_counter

                cond = node.op1
                if cond is None:
                    raise ValueError

                self.add_command(Command(CommandName.CMP, list(self.precompile_nodes(cond))))

                cond_cmd = Command(
                    Compiler.cmp_node_type_to_command_map[cond.node_type], [Operand(OperandAddress.DIRECT_LOAD, 0)]
                )

                self.add_command(cond_cmd)

                false_cmd = Command(CommandName.JMP, [Operand(OperandAddress.DIRECT_LOAD, 0)])
                self.add_command(false_cmd)

                cond_cmd.operands[0] = Operand(OperandAddress.DIRECT_LOAD, self.command_counter)

                self.compile_node(node.op2)

                self.add_command(Command(CommandName.JMP, [Operand(OperandAddress.DIRECT_LOAD, loop_start)]))

                false_cmd.operands[0] = Operand(OperandAddress.DIRECT_LOAD, self.command_counter)

            case NodeType.IF:

                if node.op1 is None:
                    raise ValueError

                self.add_command(Command(CommandName.CMP, list(self.precompile_nodes(node.op1))))

                cond_cmd = Command(
                    Compiler.cmp_node_type_to_command_map[node.op1.node_type], [Operand(OperandAddress.DIRECT_LOAD, 0)]
                )

                self.add_command(cond_cmd)

                false_cmd = Command(CommandName.JMP, [Operand(OperandAddress.DIRECT_LOAD, 0)])
                self.add_command(false_cmd)

                cond_cmd.operands[0] = Operand(OperandAddress.DIRECT_LOAD, self.command_counter)
                self.compile_node(node.op2)

                false_cmd.operands[0] = Operand(OperandAddress.DIRECT_LOAD, self.command_counter)

            case NodeType.READ:
                value = node.op1
                if value is None:
                    raise ValueError

                assert value.node_type == NodeType.VARIABLE, f"Cannot read into {value.node_type}"

                operand = self.precompile_node(value)

                self.add_command(
                    Command(
                        CommandName.IN,
                        [Operand(OperandAddress.DIRECT_LOAD, 0)]
                    )
                )

                self.add_command(
                    Command(
                        CommandName.MOV,
                        [Operand(OperandAddress.REGISTER, 2), Operand(OperandAddress.DIRECT_LOAD, operand.value)]
                    )
                )

                self.add_command(
                    Command(
                        CommandName.ST,
                        [Operand(OperandAddress.REGISTER, 2), Operand(OperandAddress.REGISTER, 3)]
                    )
                )

            case NodeType.PRINT:
                if node.op1 is None:
                    raise ValueError

                value = node.op1

                if value.node_type == NodeType.STRING_CONST:
                    operand = self.precompile_node(value)

                    self.add_command(  # address
                        Command(
                            CommandName.MOV,
                            [Operand(OperandAddress.REGISTER, 2),
                             operand]
                        )
                    )

                    loop_start = self.command_counter

                    self.add_command(
                        Command(
                            CommandName.LD,
                            [Operand(OperandAddress.REGISTER, 3),
                             Operand(OperandAddress.REGISTER, 2)]
                        )
                    )

                    self.add_command(
                        Command(
                            CommandName.CMP,
                            [Operand(OperandAddress.REGISTER, 3), Operand(OperandAddress.DIRECT_LOAD, 0x0)]
                        )
                    )

                    jmp = Command(
                        CommandName.JE,
                        [Operand(OperandAddress.DIRECT_LOAD, 0)]
                    )

                    self.add_command(jmp)

                    self.add_command(Command(CommandName.OUT, [Operand(OperandAddress.DIRECT_LOAD, 1)]))

                    self.add_command(
                        Command(
                            CommandName.INC,
                            [Operand(OperandAddress.REGISTER, 2)]
                        )
                    )

                    self.add_command(
                        Command(
                            CommandName.JMP,
                            [Operand(OperandAddress.DIRECT_LOAD, loop_start)]
                        )
                    )

                    jmp.operands[0] = Operand(OperandAddress.DIRECT_LOAD, self.command_counter)

                elif value.node_type == NodeType.VARIABLE:

                    operand = self.precompile_node(value)
                    addr = operand.value

                    v_name = value.value
                    if v_name not in self.variables_type:
                        raise ValueError(f'Unknown variable: {v_name}')

                    match self.variables_type[v_name]:
                        case "int":

                            self.add_command(  # address
                                Command(
                                    CommandName.MOV,
                                    [Operand(OperandAddress.REGISTER, 2),
                                     Operand(OperandAddress.DIRECT_LOAD, addr + 4)]
                                )
                            )

                            loop_start = self.command_counter

                            self.add_command(
                                Command(
                                    CommandName.DEC,
                                    [Operand(OperandAddress.REGISTER, 2)]
                                )
                            )

                            # out H half
                            self.add_command(
                                Command(
                                    CommandName.LD,
                                    [Operand(OperandAddress.REGISTER, 3),
                                     Operand(OperandAddress.REGISTER, 2)]
                                )
                            )

                            self.add_command(
                                Command(
                                    CommandName.SHR,
                                    [Operand(OperandAddress.REGISTER, 3), Operand(OperandAddress.DIRECT_LOAD, 4)]
                                )
                            )

                            self.add_command(
                                Command(
                                    CommandName.CMP,
                                    [Operand(OperandAddress.REGISTER, 3), Operand(OperandAddress.DIRECT_LOAD, 0xA)]
                                )
                            )

                            ge_jmp = Command(
                                CommandName.JAE,
                                [Operand(OperandAddress.DIRECT_LOAD, 0)]
                            )

                            self.add_command(ge_jmp)

                            self.add_command(
                                Command(
                                    CommandName.ADD1,
                                    [Operand(OperandAddress.REGISTER, 3), Operand(OperandAddress.DIRECT_LOAD, 0x30)]
                                )
                            )

                            jmp = Command(
                                CommandName.JMP,
                                [Operand(OperandAddress.DIRECT_LOAD, 0)]
                            )

                            self.add_command(jmp)

                            ge_jmp.operands[0] = Operand(OperandAddress.DIRECT_LOAD, self.command_counter)

                            self.add_command(
                                Command(
                                    CommandName.ADD1,
                                    [Operand(OperandAddress.REGISTER, 3), Operand(OperandAddress.DIRECT_LOAD, 0x57)]
                                )
                            )

                            jmp.operands[0] = Operand(OperandAddress.DIRECT_LOAD, self.command_counter)

                            self.add_command(Command(CommandName.OUT, [Operand(OperandAddress.DIRECT_LOAD, 1)]))

                            # out L half
                            self.add_command(
                                Command(
                                    CommandName.LD,
                                    [Operand(OperandAddress.REGISTER, 3),
                                     Operand(OperandAddress.REGISTER, 2)]
                                )
                            )

                            self.add_command(
                                Command(
                                    CommandName.SHL,
                                    [Operand(OperandAddress.REGISTER, 3), Operand(OperandAddress.DIRECT_LOAD, 4)]
                                )
                            )

                            self.add_command(
                                Command(
                                    CommandName.SHR,
                                    [Operand(OperandAddress.REGISTER, 3), Operand(OperandAddress.DIRECT_LOAD, 4)]
                                )
                            )

                            self.add_command(
                                Command(
                                    CommandName.CMP,
                                    [Operand(OperandAddress.REGISTER, 3), Operand(OperandAddress.DIRECT_LOAD, 0xA)]
                                )
                            )

                            ge_jmp = Command(
                                CommandName.JAE,
                                [Operand(OperandAddress.DIRECT_LOAD, 0)]
                            )

                            self.add_command(ge_jmp)

                            self.add_command(
                                Command(
                                    CommandName.ADD1,
                                    [Operand(OperandAddress.REGISTER, 3), Operand(OperandAddress.DIRECT_LOAD, 0x30)]
                                )
                            )

                            jmp = Command(
                                CommandName.JMP,
                                [Operand(OperandAddress.DIRECT_LOAD, 0)]
                            )

                            self.add_command(jmp)

                            ge_jmp.operands[0] = Operand(OperandAddress.DIRECT_LOAD, self.command_counter)

                            self.add_command(
                                Command(
                                    CommandName.ADD1,
                                    [Operand(OperandAddress.REGISTER, 3), Operand(OperandAddress.DIRECT_LOAD, 0x57)]
                                )
                            )

                            jmp.operands[0] = Operand(OperandAddress.DIRECT_LOAD, self.command_counter)

                            self.add_command(Command(CommandName.OUT, [Operand(OperandAddress.DIRECT_LOAD, 1)]))

                            self.add_command(
                                Command(
                                    CommandName.DEC,
                                    [Operand(OperandAddress.REGISTER, 1)]
                                )
                            )

                            self.add_command(
                                Command(
                                    CommandName.CMP,
                                    [Operand(OperandAddress.REGISTER, 2), Operand(OperandAddress.DIRECT_LOAD, addr)]
                                )
                            )

                            self.add_command(
                                Command(
                                    CommandName.JNE,
                                    [Operand(OperandAddress.DIRECT_LOAD, loop_start)]
                                )
                            )

                        case "char":
                            self.add_command(
                                Command(
                                    CommandName.MOV,
                                    [Operand(OperandAddress.REGISTER, 3),
                                     Operand(OperandAddress.MEMORY_DIRECT, addr)]
                                )
                            )

                            self.add_command(Command(CommandName.OUT, [Operand(OperandAddress.DIRECT_LOAD, 1)]))

                else:
                    pass


def compile_code(source: str, dest: str) -> None:
    with open(source, encoding='utf-8') as file:
        data = file.read()

    compiler = Compiler()
    compiler.compile_node(Parser(Lexer(program=data)).parse())

    write_commands(compiler.commands, compiler.memory, dest)


if __name__ == "__main__":
    assert len(sys.argv) == 3, "Wrong arguments: translator.py <code_file> <out_file>"
    compile_code(*sys.argv[1:])
