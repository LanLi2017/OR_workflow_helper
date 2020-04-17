# step 2: split 998 cells in column Author into several columns by separator
import json
import re
from pprint import pprint

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

    def map_historyid_columns(self,undo_redo = 'past'):
        # there is no history id for step 0: create project

        history = self.get_history()
        id_list = [ID['id'] for ID in history[undo_redo]]

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

    def map_historyid_ops(self,undo_redo='past',follow_start = 0,ops=None):
        # check following history id mapping to operation
        # history id: operation name
        # history id: operations , after undo, there is no operations for future
        history = self.get_history()
        id_list = [ID['id'] for ID in history[undo_redo]]
        f_id_list = id_list[follow_start:]

        if ops:
            op_history = ops
        else:
            op_history = self.get_operations()
        f_ops = op_history

        op_name_list = [op['op'].split('/')[1] for op in f_ops]
        # f_op_name_list = op_name_list[follow_start:]

        id_opname = dict( zip(f_id_list, op_name_list))
        id_ops = dict(zip(f_id_list, f_ops))
        return id_opname,id_ops


class OPDependency(RERineOP):
    # operation name mapping to dependency/parameters
    # return dependency set (old, new)
    def __init__(self, server, projectid, history_id, undo_redo='past',follow_start = 0,ops=None):
        super().__init__(server, projectid)
        # each operation
        self.history_id = history_id
        self.follow_start = follow_start
        self.following_ops = ops
        self.undo_redo = undo_redo

    def mapping(self):
        '''

         "column-addition": opd.add_column,
        "column-split": opd.split_column,
        "column-rename": opd.rename_column,
        "column-removal": opd.remove_column
        '''
        # op_name = self.mapping_ops_name[self.history_id]
        id_opname = super().map_historyid_ops(undo_redo=self.undo_redo,follow_start=self.follow_start,ops = self.following_ops)[0]
        print(id_opname)
        print("===================")
        print(id_opname[self.history_id])
        op_name = id_opname[self.history_id]

        if op_name == 'column-addition':
            return self.add_column_d()
        elif op_name == 'column-split':
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
        ops = super().map_historyid_ops(undo_redo=self.undo_redo,follow_start=self.follow_start,ops= self.following_ops)[1]
        add_ops = ops[self.history_id]
        expression = add_ops['expression']
        add_cols = super().map_historyid_columns(undo_redo=self.undo_redo)[self.history_id]
            # self.mapping_ops_col[self.history_id]
        input_nodes = []
        try:
            input_nodes = re.findall(r"grel:cells\.(.*)\.value\s\+\scells.(.*).value",expression)
        #     regex = [（column1, column2）]
        except:
            pass

        add_d = (input_nodes,add_cols)

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

        ops = super().map_historyid_ops(undo_redo=self.undo_redo,follow_start=self.follow_start,ops= self.following_ops)[1]

        split_ops = ops[self.history_id]
        input_node = split_ops['columnName']
        # after splitting, what's the changes?
        split_cols = super().map_historyid_columns(undo_redo=self.undo_redo)[self.history_id]
        split_d = (input_node, split_cols)
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
        ops = super().map_historyid_ops(undo_redo=self.undo_redo,follow_start=self.follow_start,ops= self.following_ops)[1]
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
        ops = super().map_historyid_ops(undo_redo=self.undo_redo,follow_start=self.follow_start,ops= self.following_ops)[1]
        trans_ops = ops[self.history_id]
        prev = trans_ops['columnName']
        cur = trans_ops['columnName']
        trans_d = (prev, cur)
        print("here is text transform")
        return trans_d


# def undo_past(to_step,past):
    # input changing step -> undo step (to_step+1)
    # past: list of history: 'id':..., 'description':..., 'time':...
    # return history ids for future & past
    # undo_history_id = past[to_step]
    # cur_history = past[:to_step-1]
    # undo_history = past[to_step:]
    # cur_history_id = [ID['id'] for ID in cur_history]
    # undo_history_id = [ID['id'] for ID in undo_history]
    # return undo_history_id

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


# build tree; parent -> children
def build(idPairs):
    lookup = {}
    for pUID,uid in idPairs:
        # check if was node already added, else add now:
        this = lookup.get(uid)
        if this is None:
            this = Node(uid)  # create new Node
            lookup[uid] = this  # add this to the lookup, using id as key

        if uid != pUID:
            # set this.parent pointer to where the parent is
            parent = lookup[pUID]
            if not parent:
                # create parent, if missing
                parent = Node(pUID)
                lookup[pUID] = parent
            this.parent = parent
    # tree
    roots = [x for x in lookup.values() if x.parent is None]

    # store dependency tree into json
    data = json.dumps(roots, indent=4)
    return roots


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


# use case 1
def undo(server,projectID, step_history_id):
    # return undo dependency
    undo_opd = OPDependency(server, projectID, step_history_id, undo_redo='past')
    undo_dependency = undo_opd.mapping()
    print(f'undo dependency :{undo_dependency}')
    return undo_dependency


def undo_fol(future, complete_op_history, rewrite_step, server, projectID):
    # save future-following operation history: discard rewritten operation

    # undo_history_id_list = refineop.get_history()
    future_history_id = [ID['id'] for ID in future]
    future_ops = complete_op_history[rewrite_step:]
    f_hid_following = future_history_id[1:]
    print(f_hid_following)
    future_deps = []
    # undo: move forward, hid[n] --> opid[n-1]
    for hid in f_hid_following:
        future_opd = OPDependency(server, projectID, hid, undo_redo='future',follow_start=1,ops=future_ops)
        future_dependency = future_opd.mapping()
        future_deps.append(future_dependency)
    print(f'future dependency: {future_deps}')
    return future_deps


# there two "history" here: 1. operation history from api 2. every changes/ history with history id
def case():
    projectID = 2014260363969
    server = refine.RefineServer()
    refineop = RERineOP(server, projectID)

    # preserve complete operation history
    complete_op_history = refineop.get_operations()
    json_p = 'ori_helper.json'
    save_ops(complete_op_history, json_p)


    # undo step 3: create new column Mode_font based on column Mode and column Font_size
    rewrite_step = int(input('which step you want to rewrite: '))
    op_step = rewrite_step -1
    undo_step = rewrite_step - 2

    # get history id -> opration name
    complete_id_opname = refineop.map_historyid_ops()[0]
    complete_id_ops = refineop.map_historyid_ops()[1]

    # get history id and do undo
    history_id_list = refineop.get_history()
    hid_list = [hid['id'] for hid in history_id_list['past'] ]
    print(hid_list)
    step_history_id = hid_list[op_step]
    print(step_history_id)

    undo(server,projectID,step_history_id)
    # undo project id: prev; redo: current
    undo_project_id = hid_list[undo_step]
    # refineop.undo_project(undo_project_id)
    refineop.undo_project(undo_project_id)  # history will get changed :  {past:[]}, {future:[]}

    # undo following
    # future = refineop.get_future_history()
    # undo_fol(future,complete_op_history,rewrite_step,server,projectID)

    # undo
    # refineop.undo_project(undo_project_id)

    # # redo step 3: rename Created_time to Created
    # # redo and undo: see if the dependency changes
    # redo_name = 'column-rename'
    # old_name = 'Name 1'
    # new_name = 'Name_1'
    # # refineop.rename_column(old_name, new_name) # op and name dicts mapping needed
    # mapping_op_name_func(server,projectID)[redo_name](old_name, new_name)
    # new_history_id = refineop.get_history()
    # redo_history_id = new_history_id['past'][op_step]['id']
    #
    # redo_opd = OPDependency(server, projectID,redo_history_id)
    # redo_dependency = redo_opd.mapping()
    # print(f"redo dependency: {redo_dependency}")
    # compare undo_dep and redo_dep
    # future_op_following dependency mining
    # compatible with -undo +redo
    # check_update(future_deps, undo_dependency, redo_dependency)


def main():
    project_id = 2247657852239
    server = refine.RefineServer()
    refineop = RERineOP(server, project_id)

    # save complete operation history
    complete_history = refineop.get_operations()
    json_p = 'ori_helper.json'
    save_ops(complete_history, json_p)
    # main_wf()

    future = refineop.get_future_history()
    # undo starting id
    undo_start_id = future[0]['id']

    # check if the following operations have dependency of undo starting
    undo_following = future[1:]
    undo_fol_id_list = [ID['id'] for ID in undo_following]

    # recipe_name = 'graph_helper.json'
    # history_p = f'OpenRefineHistory/{recipe_name}'
    # load recipe from OpenRefine server
    # get_history(projectID, history_p)

    # helper(step, history_p)

    # use py-client library and apply new json


def GetColumnName():
    project_id = 1943681426967
    server = refine.RefineServer()
    OR = RERineOP(server,project_id)
    column_name=OR.get_models()
    return column_name


def test2():
    projectid = 2014260363969
    server = refine.RefineServer()
    OR = RERineOP(server, projectid)
    his = OR.get_history()
    pprint(his)
    refine.RefineProject(server,projectid).undo_project(history_id=1586814287017)
    # # 1586814914073
    # # 1586814287017
    # OR.undo_project('1586814287017')
    # OR.split_column('Name',' ')
    f = OR.get_history()
    pprint(f)


if __name__ == '__main__':
    # test()
    case()