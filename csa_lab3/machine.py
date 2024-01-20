import logging

from csa_lab3.control_unit import ControlUnit
from csa_lab3.data_path import DataPath
from csa_lab3.isa import read_commands, read_memory

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)


def simulation(binary_file_name: str, input_buffer: list[str]) -> None:
    filename = binary_file_name
    cmds = read_commands(filename)
    mem = read_memory(f'{filename}.mem')

    data_path = DataPath(in_buffer=input_buffer)
    control_unit = ControlUnit(data_path=data_path, commands=cmds, memory=mem)

    counter = 0
    try:
        while True:
            control_unit.decode_command()
            counter += 1
            logging.debug(
                "%i) %s - %s",
                counter,
                str(control_unit.commands_memory[control_unit.command_pointer]),
                str(control_unit)
            )
    except StopIteration:
        pass

    logging.info("Out buffer: %s", ''.join(data_path.stdout.buffer))

    print(''.join(data_path.stdout.buffer))
    print(f"Instructions: {counter}")


if __name__ == "__main__":
    simulation("output/hello.bin", list("unused\0"))
