def dont_block(command):
    command.block_concurrency = False
    return command


def must_block(command):
    command.block_concurrency = True
    return command
