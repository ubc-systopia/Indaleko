import operators


class Pipeline:
    def __init__(self, input_generator: operators.IReader):
        self.input_generator = input_generator
        self.operators = []

    def add(self, operator: operators.IOperator):
        self.operators.append(operator)
        return self

    def run(self):
        data_generator = self.input_generator.run()
        for data_tuple in data_generator:
            output = data_tuple
            for operator in self.operators:
                output = operator.execute(output)
            yield output
