


def readTemplates(input_path):

    template_file = open(input_path, 'r')
    template_dict = {}
    for line in template_file:
        relation, dictionary = line.split()
        relation_template_dict = eval(dictionary)
        template_dict[relation] = relation_template_dict
    return template_dict


def get_ranking(e1, r, e2):
