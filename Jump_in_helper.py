# step 2: split 998 cells in column Author into several columns by separator
import itertools
import json
import re
from pprint import pprint
import matplotlib.pyplot as plt

from graphviz import Digraph
import networkx as nx
from halp.directed_hypergraph import DirectedHypergraph
from networkx.drawing.nx_agraph import graphviz_layout

from OpenRefineClientPy3.google_refine.refine import refine


class RERineOP(refine.RefineProject):
    # inherit class from RefineProject
    def __init__(self,server, projectID):
        super().__init__(server,projectID)

    def rename_column(self, column, new_column):
        return super().rename_column(column, new_column)

    def get_operations(self):
        return super().get_operations()

    def get_history(self):
        return super().list_history()

    def get_past_history(self):
        ''' past: current history '''
        list_history = super().list_history()
        # {'future':[], 'past':[]}
        past = list_history['past']
        return past

    def get_future_history(self):
        ''' future: undo/redo part'''
        list_history = super().list_history()
        future = list_history['future']
        return future

    def get_models(self):
        # return columns
        res = super().get_models()
        columns = res['columnModel']['columns']
        # current state of the column model
        cur_col_name = [name['name'] for name in columns]
        return cur_col_name

    def init_model(self, init_historyid):
        # there is no history id for "create project"
        # we can not see what's the difference by the first step
        # by comparing the old column name and current name: we could initialize the difference
        res = super().get_models()
        columns = res['columnModel']['columns']
        cur_model = [name['name'] for name in columns]
        prev_model = [original['originalName'] for original in columns]
        diff = {
            init_historyid: list(set(cur_model) - set(prev_model))
        }

        return diff

    def undo_project(self, history_id):
        # step in ==> history id
        '''
        history_id: output from undo_past
        return current column models
        '''
        super().undo_project(history_id)
        return self.get_models()

    def remove_column(self, column):
        return

    def text_transform(self, column, expression, on_error='set-to-blank', repeat=False, repeat_count=10):
        return super().text_transform(column,expression)

    def split_column(
            self,
            column,
            separator=',',
            mode='separator',
            regex=False,
            guess_cell_type=True,
            remove_original_column=True,
    ):
        return super().split_column(column, separator, mode, regex, remove_original_column=False)

    def map_historyid_columns(self):
        # there is no history id for step 0: create project

        history = self.get_history()
        id_list = [ID['id'] for ID in history['past']]

        # initialize
        init_history = id_list[0]
        diff = self.init_model(init_history)
        # delta0 = list(set(cur_model)-set(prev_model))
        columnModel = [self.undo_project(h) for h in id_list]
        # set difference stands for corresponding changes applying each operation
        diff.update({
            id_list[idx+1]: list(set(columnModel[idx+1]) - set(columnModel[idx]))
            for idx in range(len(columnModel)-1)
        })
        last_hid = id_list[len(id_list)-1]
        self.undo_project(last_hid)
        return diff

    def map_historyid_ops(self):
        # check following history id mapping to operation
        # history id: operation name
        # history id: operations , after undo, there is no operations for future
        history = self.get_history()
        id_list = [ID['id'] for ID in history['past']]

        op_history = self.get_operations()

        op_name_list = [op['op'].split('/')[1] for op in op_history]
        # f_op_name_list = op_name_list[follow_start:]

        id_opname = dict( zip(id_list, op_name_list))
        id_ops = dict(zip(id_list, op_history))
        return id_opname,id_ops


class OPDependency(RERineOP):
    # operation name mapping to dependency/parameters
    # return dependency set (old, new)
    def __init__(self, server, projectid, history_id):
        super().__init__(server, projectid)
        # each operation
        self.history_id = history_id
        self.hid_ops = super().map_historyid_ops()
        self.hid_col = super().map_historyid_columns()

    def mapping(self):
        '''

         "column-addition": opd.add_column,
        "column-split": opd.split_column,
        "column-rename": opd.rename_column,
        "column-removal": opd.remove_column
        '''
        # op_name = self.mapping_ops_name[self.history_id]
        id_opname = self.hid_ops[0]
        op_name = id_opname[self.history_id]

        if op_name == 'column-addition':
            print("this is add")
            return self.add_column_d()
        elif op_name == 'column-split':
            print("this is split")
            return self.split_column_d()
        elif op_name == 'column-rename':
            print("rename")
            return self.rename_column_d()
        elif op_name == 'column-removal':
            return self.remove_column_d()
        elif op_name == 'text-transform':
            return self.text_transform_d()

    def add_column_d(self):
        '''
        {'baseColumnName': 'Mode',
          'columnInsertIndex': 4,
          'description': 'Create column Mode_font at index 4 based on column Mode '
                         'using expression grel:cells.Mode.value + '
                         'cells.Font_size.value',
          'engineConfig': {'facets': [], 'mode': 'row-based'},
          'expression': 'grel:cells.Mode.value + cells.Font_size.value',
          'newColumnName': 'Mode_font',
          'onError': 'set-to-blank',
          'op': 'core/column-addition'}
        '''
        # add column expressions:
        # cells["Column 1"].value + cells["Column 2"].value
        # cells.MyCol1.value + cells.MyCol2.value
        # row.record.cells.AuthorFirstName.value + " " + row.record.cells.AuthorLastName.value
        ops = self.hid_ops[1]
        add_ops = ops[self.history_id]
        expression = add_ops['expression']
        add_cols = self.hid_col[self.history_id]
            # self.mapping_ops_col[self.history_id]
        input_nodes = []
        try:
            input_nodes = re.findall(r"\.(\w+)\.",expression)
            # r"grel:cells\.(\S+)\.value\s*\+\s*\+\s*cells\.(\S+)\.value"
        #     regex = [（column1, column2）]
        except:
            # "expression": "grel:cells[\"tag 1\"].value + cells[\"tag 3\"].value",
            input_nodes = re.findall(r"\"(\w+\s*\d*)\\",expression)

        add_d = []
        child = ''.join(add_cols)
        pairs = zip(input_nodes, itertools.repeat(child))
        for pair in pairs:
            add_d.append(pair)
        return add_d

    def split_column_d(self):
        '''
         'columnName': 'Author',
         'description': '...',
         'engineConfig': {'facets': [], 'mode': 'row-based'},
         'guessCellType': True,
         'maxColumns': 0,
         'mode': 'separator',
         'op': 'core/column-split',
         'regex': False,
         'removeOriginalColumn': True,
         'separator': '#'
        incompleteness not approve : except 'desciption'

        There is no record for new generated columns in OpenRefine
        '''

        ops = self.hid_ops[1]

        split_ops = ops[self.history_id]
        input_node = split_ops['columnName']
        # after splitting, what's the changes?
        split_cols = self.hid_col[self.history_id]
        split_d = []

        parent = ''.join(input_node)
        pairs = zip(itertools.repeat(parent),split_cols)
        for pair in pairs:
            split_d.append(pair)
        return split_d

    def remove_column_d(self):
        '''
         {'columnName': 'Danmaku_pool',
          'description': 'Remove column Danmaku_pool',
          'op': 'core/column-removal'}]
        '''

        return

    def rename_column_d(self):
        '''
          'description': 'Rename column Showing_time to Video_Time',
          'newColumnName': 'Video_Time',
          'oldColumnName': 'Showing_time',
          'op': 'core/column-rename'},
        '''
        ops = self.hid_ops[1]
        rename_ops =  ops[self.history_id]
        oldcolumn = rename_ops['oldColumnName']
        newcolumn = rename_ops['newColumnName']
        # return (input, output)
        rename_d = (oldcolumn, newcolumn)
        return rename_d

    def text_transform_d(self):
        '''
           "op": "core/text-transform",
            "description": "Text transform on cells in column Author using expression value.replace(\"#\",\" \")",
            "columnName": "Author",
            "expression": "value.replace(\"#\",\" \")",
        '''
        ops =self.hid_ops[1]
        trans_ops = ops[self.history_id]
        prev = trans_ops['columnName']
        cur = trans_ops['columnName']
        trans_d = (prev, cur)
        print("here is text transform")
        return trans_d


# build tree
class Node(dict):
    def __init__(self,uid):
        super().__init__()
        self._parent = None # pointer to parent Node
        self['id'] = uid # keep reference to id #
        self['children'] = [] # collection of pointers to child nodes

    @property
    def parent(self):
        return self._parent # simply return the object at the _parent

    @parent.setter
    def parent(self,node):
        self._parent = node
        # add this node to parent's list of children
        node['children'].append(self)


def mapping_op_name_func(server, projectID):
    # map operation name and refine function
    refineop = RERineOP(server,projectID)

    return {
        'column-rename': refineop.rename_column,
        'column-split': refineop.split_column,
        'column-addition': refineop.add_column,
        'column-removal': refineop.remove_column,
        'text-transform': refineop.text_transform,
    }


def helper(step, path):
    with open(path, 'r')as f:
        data = json.load(f)

    pprint(data[step])


def save_ops(ops,json_p):
    '''this is for saving the operation history from being rewritten by redo'''
    with open(f'OpenRefineHistory/{json_p}','w')as f:
        json.dump(ops, f,indent=4)


# preprocess id: e.g. when text-transformation, input and output are the same
# in case of "circle" problem
def name_pairs_to_id_pairs(name_pairs):
    name_ids = {}
    id_counter = itertools.count()
    id_pairs = []
    for name_u, name_v in name_pairs:
        id_u = name_ids.setdefault(name_u, next(id_counter))
        id_v = name_ids[name_v] = next(id_counter)
        id_pairs.append((id_u, id_v))
    return id_pairs


# build tree; parent -> children
def build(id_pairs):
    nodes = {}
    for id_u, id_v in id_pairs:
        node_u = nodes.setdefault(id_u, Node(id_u))
        node_v = nodes.setdefault(id_v, Node(id_v))
        node_v.parent = node_u
    return nodes


# recursively extract children node
# extract_ids(roots, lambda x: x['id'] == 2)
def extract_ids(items, condition):
    ids = []
    for item in items:
        if condition(item):
            ids.append(item['id'])
            ids += extract_ids(item['children'], lambda x: True)
        else:
            ids += extract_ids(item['children'], condition)

    return ids


def check_update(future_dep, undo_dep, redo_dep):
    '''
    future_dep: list [(step1_input, step1_output),...]
    undo_dep : undo node dependency
    redo_dep: redo node dependency
    '''
    # logic of dependency checking
    # old_dep : input node; new_dep : output node
    # undo influence: (old_dep, new_dep): compare undo.new_dep with following.old_dep
    # discard if exists
    # redo influence: (old_dep, new_dep): compare redo.old_dep with following.old_dep
    # update if exists
    undo_input = undo_dep[0]
    undo_ouput = undo_dep[1] # influence

    redo_input = redo_dep[0] # influence
    redo_output = redo_dep[1]

    # we care about the input of the following steps
    prev_input = [f[0] for f in future_dep]
    prev_output = [f[1] for f in future_dep]

    # input should be recursively checking

    for dep in prev_input:

        pass
    if undo_input == redo_input & undo_ouput == redo_output:

        pass
    elif undo_input == redo_input & undo_ouput != redo_output:
        # check if input of following == undo_output

        pass
    elif undo_input != redo_input & undo_ouput != redo_output:
        '''    '''

        pass
    elif undo_input != redo_input & undo_ouput == redo_output:
        pass


def dependency():
    projectID = 2014260363969
    server = refine.RefineServer()
    refineop = RERineOP(server, projectID)

    # preserve complete operation history
    complete_op_history = refineop.get_operations()
    json_p = 'ori_helper.json'
    save_ops(complete_op_history, json_p)

    # get history id -> opration name
    hid_opname= refineop.map_historyid_ops()[0]
    hid_ops = refineop.map_historyid_ops()[1]

    # get history id and do undo
    history_id_list = refineop.get_history()
    hid_list = [hid['id'] for hid in history_id_list['past']]
    print(hid_list)

    dep_list = []
    for hid in hid_list:
        opd = OPDependency(server, projectID, hid)
        dep = opd.mapping()
        if isinstance(dep,list):
            dep_list += dep
        elif isinstance(dep,tuple):
            dep_list.append(dep)

    return dep_list


def tree_dep(pairs):
    lookup = build(pairs)  # can look at any node from here.

    roots = [x for x in lookup.values() if x.parent is None]
    pprint(roots)
    # and for nice visualization:
    # import json
    # data = json.dumps(roots, indent=4)
    # print(json.dumps(roots, indent=4))


def graph():
    # G = nx.Graph()
    # G.add_edges_from(id_pairs)
    # nx.draw_networkx(G, with_labels=True)
    # plt.show()
    e = Digraph()
    e.attr('node', shape='ellipse')
    e.node('Date (CST)')
    e.node('Date (CST)1')
    e.node('Author')
    e.node('Author1')
    e.node('Author2')
    e.node('Author_Name')
    e.node('Author_Name1')
    e.edge('Date (CST)','Date (CST)1')
    e.edge('Author','Author1')
    e.edge('Author1','Author2')
    e.edge('Author2','Author_Name')
    e.edge('Name', 'Author_Name')
    e.edge('Author_Name','Author_Name1')

    e.view()


def graph_id():
    e = Digraph()
    e.attr('node', shape='ellipse')
    e.node('0')
    e.node('1')
    e.node('2')
    e.node('3')
    e.node('5')
    e.node(7)
    e.node(8)
    e.node(9)
    e.node(11)

    e.edge(0,1)
    e.edge(2,3)
    e.edge(3,5)
    e.edge(5,7)
    e.edge(8,9)
    e.edge(9,11)

    e.view()


def hyperdep():
    # hyper graph of dependency

    # initialize an empty hypergraph
    G = nx.DiGraph()

    G.add_edge('Date (CST)','Date (CST)1', weight=0.6, length=25)
    G.add_edge('Author','Author2',weight=0.9)
    G.add_edge('Author2','Author3', weight =0.8)
    # (Author, Name) -> (Author_Name)
    G.add_edge('Author3','Author_Name', weight = 0.2)
    G.add_edge('Name', 'Author_Name', weight = 0.1, length = 24)
    G.add_edge('Author3', 'Name', weight = 0.3, length = 25)
    G.add_edge('Author_Name','Author_Name5',weight=0.7, length= 20)

    elarge = [(u,v) for (u,v,d) in G.edges(data=True) if d['weight']>0.5]
    esmall = [(u,v) for (u,v,d) in G.edges(data=True) if d['weight']<=0.5]

    pos = nx.spring_layout(G, k=0.15,iterations=20)  # positions for all ndoes
    plt.figure(figsize=(24,30))

    # nodes
    nx.draw_networkx_nodes(G, pos, node_size=700, nodelist=['Date (CST)', 'Date (CST)1', 'Author','Author2','Author_Name5' ],
                           node_color='blue')
    nx.draw_networkx_nodes(G, pos, node_size=1400, nodelist=['Author3', 'Name', 'Author_Name'],
                           node_color='yellow', node_shape='*')

    # edges

    nx.draw_networkx_edges(G, pos, edgelist=elarge,
                           width=6)
    nx.draw_networkx_edges(G, pos, edgelist=esmall,
                           width=6, alpha=0.5, edge_color='b', style='dashed')

    # labels
    nx.draw_networkx_labels(G, pos, font_size=25, font_family='sans-serif', font_color='red', font_weight='bold',
                            labels={'Date (CST)': 'Date (CST)', 'Date (CST)1': 'Date (CST)1', 'Author': 'Author',
                                    'Author2':'Author2', 'Author_Name5':'Author_Name5'})
    nx.draw_networkx_labels(G, pos, font_size=25, font_family='sans-serif', font_color='red', font_weight='bold',
                            labels={'Author3': 'Author3', 'Name': 'Name', 'Author_Name': 'Author_Name'})

    plt.axis('off')
    plt.savefig('hyper.png')
    plt.show()


if __name__ == '__main__':
    # name_pairs = dependency()
    # [
    # ('Date (CST)', 'Date (CST)'),
    # ('Author', 'Author'),
    # ('Author', 'Author'),
    # ('Author', 'Author_Name'),
    # ('Name', 'Author_Name'),
    # ('Author_Name', 'Author_Name')
    # ]
    # graph()
    # id_pairs = name_pairs_to_id_pairs(name_pairs)
    # print(id_pairs)
    # graph()
    # graph_id()
    # pprint(id_pairs)
    # tree_dep(id_pairs)
    # graph(id_pairs)
    hyperdep()