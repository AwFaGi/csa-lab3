from csa_lab3.data_path import DataPath, AluOperation, Register
from csa_lab3.isa import CommandName, Command, MemoryWord, OperandAddress


class ControlUnit:
    def __init__(self, data_path: DataPath, commands: list[Command], memory: list[MemoryWord]):
        self.data_path = data_path
        self.data_path.data_memory.fill_data(memory)

        self.commands_memory = {}
        self.command_addresses = []

        for cmd in commands:
            self.commands_memory[cmd.address] = cmd
            self.command_addresses.append(cmd.address)

        self.command_pointer = 0

    def _move(self, from_register: Register, to_register: Register | list[Register]) -> None:
        if not isinstance(to_register, list):
            to_register = [to_register]

        from_register.open_out()
        for reg in to_register:
            reg.open_in()

        # self.data_path.command_bus.perform_transfer()
        self.data_path.data_bus.perform_transfer()

        from_register.close_out()
        for reg in to_register:
            reg.close_in()

    def read_from_mem(self, address_reg: Register, to_register: Register) -> None:
        self._move(address_reg, self.data_path.DP)
        self.data_path.data_memory.signal_read()
        self._move(self.data_path.DR, to_register)

    def write_to_mem(self, address_reg: Register, data_register: Register) -> None:
        self._move(address_reg, self.data_path.DP)
        self._move(data_register, self.data_path.DR)
        self.data_path.data_memory.signal_write()

    def _next_command(self, value: int | None = None) -> None:
        if value:
            self.command_pointer = value
        else:
            self.command_pointer = self.command_addresses[self.command_addresses.index(self.command_pointer) + 1]

    def register_num_to_register(self, s: int) -> Register:
        match s:
            case 0:
                return self.data_path.AC
            case 1:
                return self.data_path.BR
            case 2:
                return self.data_path.R0
            case 3:
                return self.data_path.IOR
            case _:
                raise ValueError(f"Unknown register: {s}")

    def decode_command(self) -> None:
        command = self.commands_memory[self.command_pointer]
        command_name = command.name

        match command_name:
            case CommandName.NOP:
                pass

            case CommandName.HLT:
                raise StopIteration

            case CommandName.MOV:

                source = command.operands[1]
                match source.address:
                    case OperandAddress.DIRECT_LOAD:
                        self.data_path.AC.set_value(source.value)
                    case OperandAddress.MEMORY_DIRECT:
                        self.data_path.AC.set_value(source.value)
                        self.read_from_mem(self.data_path.AC, self.data_path.AC)

                dest = command.operands[0]
                match dest.address:
                    case OperandAddress.DIRECT_LOAD:
                        self.data_path.BR.set_value(dest.value)
                        self.write_to_mem(self.data_path.BR, self.data_path.AC)
                    case OperandAddress.MEMORY_DIRECT:
                        self.data_path.BR.set_value(dest.value)
                        # self.read_from_mem(self.data_path.BR, self.data_path.BR)
                        self.write_to_mem(self.data_path.BR, self.data_path.AC)
                    case OperandAddress.REGISTER:
                        self._move(self.data_path.AC, self.register_num_to_register(dest.value))

            case CommandName.MOV4:

                source = command.operands[1]
                dest = command.operands[0]

                assert dest.address == OperandAddress.MEMORY_DIRECT, "Insensible move"

                if source.address == OperandAddress.DIRECT_LOAD:
                    self.data_path.AC.set_value(source.value)
                    self.data_path.BR.set_value(dest.value)

                    self.write_to_mem(self.data_path.BR, self.data_path.AC)
                    self.data_path.AC.set_value(0)

                    for i in range(1, 4):
                        self._move(self.data_path.BR, self.data_path.INR)
                        self.data_path.alu.perform_operation(AluOperation.INCR)
                        self._move(self.data_path.OUT, self.data_path.BR)

                        self.write_to_mem(self.data_path.BR, self.data_path.AC)

                elif source.address == OperandAddress.MEMORY_DIRECT:
                    self.data_path.AC.set_value(source.value)
                    self._move(self.data_path.AC, self.data_path.R0)

                    self.data_path.BR.set_value(dest.value)

                    for i in range(0, 4):
                        self.read_from_mem(self.data_path.R0, self.data_path.AC)
                        self.write_to_mem(self.data_path.BR, self.data_path.AC)

                        self._move(self.data_path.R0, self.data_path.INR)
                        self.data_path.alu.perform_operation(AluOperation.INCR)
                        self._move(self.data_path.OUT, self.data_path.R0)

                        self._move(self.data_path.BR, self.data_path.INR)
                        self.data_path.alu.perform_operation(AluOperation.INCR)
                        self._move(self.data_path.OUT, self.data_path.BR)

            case CommandName.ADD1:
                source_r = command.operands[1]
                dest = command.operands[0]

                assert dest.address == OperandAddress.REGISTER, "Bad add1"
                assert source_r.address == OperandAddress.DIRECT_LOAD, "Bad add1"

                self.data_path.alu.flags['C'] = 0
                self._move(self.register_num_to_register(dest.value), self.data_path.INL)
                self.register_num_to_register(dest.value).set_value(source_r.value)
                self._move(self.register_num_to_register(dest.value), self.data_path.INR)

                self.data_path.alu.perform_operation(AluOperation.ADD)
                self._move(self.data_path.OUT, self.register_num_to_register(dest.value))

            case CommandName.ADD:
                operation = AluOperation.ADD

                source_l = command.operands[1]
                source_r = command.operands[2]
                dest = command.operands[0]

                assert dest.address == OperandAddress.MEMORY_DIRECT, "Insensible add"

                self.data_path.alu.flags['C'] = 0

                expand_sl = False
                expand_sr = False

                self.data_path.AC.set_value(dest.value)

                self.data_path.BR.set_value(source_l.value)
                if source_l.address == OperandAddress.DIRECT_LOAD:
                    self.data_path.INL.set_value(source_l.value)
                    expand_sl = True
                else:
                    self.read_from_mem(self.data_path.BR, self.data_path.INL)

                self.data_path.R0.set_value(source_r.value)
                if source_r.address == OperandAddress.DIRECT_LOAD:
                    self.data_path.INR.set_value(source_r.value)
                    expand_sr = True
                else:
                    self.read_from_mem(self.data_path.R0, self.data_path.INR)

                for i in range(0, 4):

                    self.data_path.alu.perform_operation(operation)

                    self.write_to_mem(self.data_path.AC, self.data_path.OUT)

                    self._move(self.data_path.AC, self.data_path.INR)
                    self.data_path.alu.perform_operation(AluOperation.INCR)
                    self._move(self.data_path.OUT, self.data_path.AC)

                    if not expand_sl:
                        self._move(self.data_path.BR, self.data_path.INR)
                        self.data_path.alu.perform_operation(AluOperation.INCR)
                        self._move(self.data_path.OUT, self.data_path.BR)

                        self.read_from_mem(self.data_path.BR, self.data_path.INL)
                    else:
                        self.data_path.INL.set_value(0)

                    if not expand_sr:
                        self._move(self.data_path.R0, self.data_path.INR)
                        self.data_path.alu.perform_operation(AluOperation.INCR)
                        self._move(self.data_path.OUT, self.data_path.R0)
                        self.read_from_mem(self.data_path.R0, self.data_path.INR)
                    else:
                        self.data_path.INR.set_value(0)

            case CommandName.SUB:
                operation = AluOperation.SUB

                source_l = command.operands[1]
                source_r = command.operands[2]
                dest = command.operands[0]

                assert dest.address == OperandAddress.MEMORY_DIRECT, "Insensible sub"
                assert source_l.address == OperandAddress.DIRECT_LOAD, "Currently, not supported"

                self.data_path.AC.set_value(dest.value)
                self.data_path.INL.set_value(source_l.value)

                self.data_path.R0.set_value(source_r.value)
                self.read_from_mem(self.data_path.R0, self.data_path.INR)

                self.data_path.alu.perform_operation(operation)
                self.write_to_mem(self.data_path.AC, self.data_path.OUT)

            case CommandName.CMP:
                operation = AluOperation.SUB

                source_l = command.operands[0]
                source_r = command.operands[1]

                if (source_l.address == OperandAddress.MEMORY_DIRECT
                        and source_r.address == OperandAddress.MEMORY_DIRECT):

                    self.data_path.AC.set_value(source_l.value)
                    self.data_path.BR.set_value(source_r.value)

                    for i in range(3):
                        self._move(self.data_path.AC, self.data_path.INR)
                        self.data_path.alu.perform_operation(AluOperation.INCR)
                        self._move(self.data_path.OUT, self.data_path.AC)

                        self._move(self.data_path.BR, self.data_path.INR)
                        self.data_path.alu.perform_operation(AluOperation.INCR)
                        self._move(self.data_path.OUT, self.data_path.BR)

                    for i in range(4):
                        self.read_from_mem(self.data_path.AC, self.data_path.INL)
                        self.read_from_mem(self.data_path.BR, self.data_path.INR)

                        self.data_path.alu.perform_operation(operation)

                        if self.data_path.alu.flags['Z'] == 0 or i == 3:
                            break

                        self._move(self.data_path.AC, self.data_path.INR)
                        self.data_path.alu.perform_operation(AluOperation.DECR)
                        self._move(self.data_path.OUT, self.data_path.AC)

                        self._move(self.data_path.BR, self.data_path.INR)
                        self.data_path.alu.perform_operation(AluOperation.DECR)
                        self._move(self.data_path.OUT, self.data_path.BR)

                elif (source_l.address == OperandAddress.REGISTER
                      and source_r.address == OperandAddress.DIRECT_LOAD):

                    self._move(self.register_num_to_register(source_l.value), self.data_path.INL)

                    if self.register_num_to_register(source_l.value) != self.data_path.AC:
                        self.data_path.AC.set_value(source_r.value)
                        self._move(self.data_path.AC, self.data_path.INR)
                    else:
                        self.data_path.BR.set_value(source_r.value)
                        self._move(self.data_path.BR, self.data_path.INR)

                    self.data_path.alu.perform_operation(AluOperation.SUB)

                else:
                    raise ValueError("Currently, not supported")

            case CommandName.SHL | CommandName.SHR:
                alu_op = AluOperation.SHL if command_name == CommandName.SHL else AluOperation.SHR

                source_l = command.operands[0]
                source_r = command.operands[1]

                assert source_l.address == OperandAddress.REGISTER, "Currently, not supported"
                assert source_r.address == OperandAddress.DIRECT_LOAD, "Currently, not supported"

                self._move(self.register_num_to_register(source_l.value), self.data_path.INL)

                self.data_path.AC.set_value(source_r.value)
                self._move(self.data_path.AC, self.data_path.INR)

                self.data_path.alu.perform_operation(alu_op, "C")
                self._move(self.data_path.OUT, self.register_num_to_register(source_l.value))

            case CommandName.DEC:
                dest = command.operands[0]
                assert dest.address == OperandAddress.REGISTER, "Currently, not supported"

                self._move(self.register_num_to_register(dest.value), self.data_path.INL)
                self.data_path.alu.perform_operation(AluOperation.DECL)
                self._move(self.data_path.OUT, self.register_num_to_register(dest.value))

            case CommandName.INC:
                dest = command.operands[0]
                assert dest.address == OperandAddress.REGISTER, "Currently, not supported"

                self._move(self.register_num_to_register(dest.value), self.data_path.INL)
                self.data_path.alu.perform_operation(AluOperation.INCL)
                self._move(self.data_path.OUT, self.register_num_to_register(dest.value))

            case CommandName.LD:
                to_ = command.operands[0]
                from_ = command.operands[1]

                assert to_.address == OperandAddress.REGISTER, "Currently, not supported"
                assert from_.address == OperandAddress.REGISTER, "Currently, not supported"

                self.read_from_mem(self.register_num_to_register(from_.value), self.register_num_to_register(to_.value))

            case CommandName.ST:
                to_ = command.operands[0]
                from_ = command.operands[1]

                assert to_.address == OperandAddress.REGISTER, "Currently, not supported"
                assert from_.address == OperandAddress.REGISTER, "Currently, not supported"

                self.write_to_mem(self.register_num_to_register(to_.value), self.register_num_to_register(from_.value))

            case CommandName.OUT:
                port = command.operands[0]

                self.data_path.ports[port.value].register.set_value(self.data_path.IOR.get_value())
                self.data_path.ports[port.value].after_perform_action()

            case CommandName.IN:
                port = command.operands[0]

                self.data_path.IOR.set_value(self.data_path.ports[port.value].register.get_value())
                self.data_path.ports[port.value].after_perform_action()

            case CommandName.JE:
                if self.data_path.alu.flags['Z'] == 1:
                    self._next_command(command.operands[0].value)
                    return

            case CommandName.JNE:
                if self.data_path.alu.flags['Z'] == 0:
                    self._next_command(command.operands[0].value)
                    return

            case CommandName.JAE:
                if self.data_path.alu.flags['N'] == 0:
                    self._next_command(command.operands[0].value)
                    return

            case CommandName.JMP:
                self._next_command(command.operands[0].value)
                return

            case _:
                raise NotImplementedError(f'No info about execution {command_name}')

        self._next_command()

    def __str__(self) -> str:
        registers = list(
            map(str, self.data_path.data_bus.registers)
        )
        registers.sort()
        registers.append(self.data_path.alu.flags_str())
        return " | ".join(registers)
