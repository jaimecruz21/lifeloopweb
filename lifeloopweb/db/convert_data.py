# pylint: disable=unsubscriptable-object
import json

from lifeloopweb.db import utils


def convert_data(path):
    models = {}
    with open(path, 'r') as f:
        current_model = None
        current_columns = None
        spacer_line = False
        column_widths = None
        for line in f:
            if line == "\n":
                current_model = None
                current_columns = None
                column_widths = None
            else:
                if not current_model:
                    columns = line.split()
                    current_model = columns[0]
                    current_model = current_model[:current_model.rindex("ID")]
                    current_columns = [utils.to_snake_case(c.strip())
                                       for c in columns]
                    models.setdefault(current_model,
                                      {"columns": current_columns, "data": []})
                    spacer_line = True
                elif spacer_line:
                    spacer_line = False
                    column_widths = [len(c) for c in line.split(' ')]
                else:
                    last_offset = 0
                    data = {}
                    for idx, width in enumerate(column_widths):
                        column = line[last_offset:last_offset + width-1]
                        data[current_columns[idx]] = column.strip()
                        # Don't forget the space between columns
                        last_offset = last_offset + width + 1
                    models[current_model]["data"].append(data)

    with open("{}.json".format(path), 'w') as f:
        json.dump(models, f, sort_keys=True, indent=4, separators=(',', ": "))
