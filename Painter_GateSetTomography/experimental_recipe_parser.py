def parse_gst_file(path):
    pygsti_to_driver_labels_dict = {
        'y': 'y2p',
        'x': 'x2p',
        'ypi': 'yp',
        'i': 'id',
    }

    # utility function for expanding germs, assumes that there is a germ in the
    # given experiment string, as specified by a number of gates being enclosed
    # in parentheses
    def expand_germ(experiment_string):
        germ_repetitions = 1
        # if specified in the experiment string, set 
        if '^' in experiment_string:
            temp = experiment_string.split('^')
            next_G_index = temp[1].find('G')
            if next_G_index > -1:
                numerical_substring = temp[1][0:next_G_index]
                measurement_basis_substring = temp[1][next_G_index:]
            else:
                numerical_substring = temp[1]
                measurement_basis_substring = ''
            germ_repetitions = int(numerical_substring.strip())
            experiment_string = temp[0] + measurement_basis_substring
        
        if experiment_string[0] == '(':
            temp_1 = experiment_string[1:]
            prep = ''
            temp_2 = temp_1.split(')')
        else:
            temp_1 = experiment_string.split('(')
            prep = temp_1[0]
            temp_2 = temp_1[1].split(')')
        
        germ = temp_2[0]

        if len(temp_2) > 1:
            measure = temp_2[1]
        else:
            measure = ''

        expanded_germs = ''
        for i in range(germ_repetitions):
            expanded_germs += germ        

        return (prep + expanded_germs + measure).strip()

    experiments = []
    with open(path) as f:
        for line in f:
            experiment_string = line.split()[0]

            if '#' in experiment_string:
                continue

            elif '{}' in experiment_string:
                experiments.append(['noop'])
                continue

            elif '(' in experiment_string:
                experiment_string = expand_germ(experiment_string)

            # Annoyingly split will return an initial empty string when the
            # split character is the first character of the string being split
            gates = experiment_string[1:].split('G')
            experiments.append([pygsti_to_driver_labels_dict[gate_label] for
                                    gate_label in gates])

    return experiments

if __name__=="__main__":
    parse_gst_file('data/dataset.txt')
