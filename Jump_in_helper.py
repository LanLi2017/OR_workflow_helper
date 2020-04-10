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

    def redo_project(self, history_id):
        return super().redo_project(history_id)

    def remove_column(self):
        return

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
        return diff

    def map_historyid_ops(self,undo_redo='past',follow_start = 0):
        # check following history id mapping to operation
        # history id: operation name
        # history id: operations
        history = self.get_history()
        pprint(f"history can not find :{history}")
        id_list = [ID['id'] for ID in history[undo_redo]]
        id_list1 = [ID['id'] for ID in history['future']]
        pprint(f"hello : {id_list1}")

        print(f"id can not find in :{id_list}")
        f_id_list = id_list[follow_start:]

        op_history = self.get_operations()
        f_ops = op_history
        op_name_list = [op['op'].split('/')[1] for op in op_history]
        f_op_name_list = op_name_list[follow_start:]

        id_opname = dict( zip(f_id_list, f_op_name_list))
        id_ops = dict(zip(f_id_list, f_ops))
        return id_opname,id_ops


class OPDependency(RERineOP):
    # operation name mapping to dependency/parameters
    # return dependency set (old, new)
    def __init__(self, server,projectid, history_id, undo_redo='past'):
        super().__init__(server, projectid)
        # each operation
        self.history_id = history_id
        self.mapping_ops_col = super().map_historyid_columns()
        # self.mapping_ops_name = super().map_historyid_ops(undo_redo)[0]
        # self.mapping_ops = super().map_historyid_ops()[1]
        self.undo_redo = undo_redo

    def mapping(self):
        '''

         "column-addition": opd.add_column,
        "column-split": opd.split_column,
        "column-rename": opd.rename_column,
        "column-removal": opd.remove_column
        '''
        # op_name = self.mapping_ops_name[self.history_id]
        op_name = super().map_historyid_ops(undo_redo=self.undo_redo)[0]
        if op_name =='column-addition':
            return self.add_column_d()
        elif op_name == 'column-split':
            return self.split_column_d()
        elif op_name == 'column-rename':
            return self.rename_column_d()
        elif op_name == 'column-removal':
            return self.remove_column_d()

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
        ops = super().map_historyid_ops(undo_redo=self.undo_redo)[1]
        add_ops = ops[self.history_id]
        expression = add_ops['expression']
        add_cols = self.mapping_ops_col[self.history_id]
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

        split_ops = super().map_historyid_ops(undo_redo=self.undo_redo)[1]
        input_node = split_ops['columnName']
        # after splitting, what's the changes?
        split_cols = self.mapping_ops_col[self.history_id]
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
        rename_ops = super().map_historyid_ops(undo_redo=self.undo_redo)[1]
        oldcolumn = rename_ops['oldColumnName']
        newcolumn = rename_ops['newColumnName']
        # return (input, output)
        rename_d = (oldcolumn, newcolumn)
        return rename_d


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


def mapping_op_name_func(server, projectID):
    # map operation name and refine function
    refineop = RERineOP(server,projectID)

    return {
        'column-rename': refineop.rename_column,
        'column-split': refineop.split_column,
        'column-addition': refineop.add_column,
        'column-removal': refineop.remove_column
    }


def helper(step, path):
    with open(path, 'r')as f:
        data = json.load(f)

    pprint(data[step])


def save_ops(ops,json_p):
    '''this is for saving the operation history from being rewritten by redo'''
    with open(f'OpenRefineHistory/{json_p}','w')as f:
        json.dump(ops, f,indent=4)


def check_update(future_dep, undo_dep, redo_dep):
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

    future_dep_input = future_dep[0] # input should be recursively checking

    if undo_input==redo_input & undo_ouput==redo_output:
        pass
    elif undo_input==redo_input & undo_ouput!=redo_output:
        pass
    elif undo_input!=redo_input & undo_ouput!=redo_output:
        '''    '''

        pass
    elif undo_input!=redo_input & undo_ouput==redo_output:
        pass


# use case 1
# there two "history" here: 1. operation history from api 2. every changes/ history with history id
def case():
    projectID = 2247657852239
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
    step_history_id = history_id_list['past'][op_step]['id']

    # return undo dependency
    undo_opd = OPDependency(server, projectID, step_history_id)
    undo_dependency = undo_opd.mapping()
    print(f'undo dependency: {undo_dependency}')

    undo_id = history_id_list['past'][undo_step]['id']
    refineop.undo_project(undo_id) # history will get changed :  {past:[]}, {future:[]}
    #

    # save future-following operation history: discard rewritten operation
    # future = refineop.get_future_history()
    undo_history_id_list = refineop.get_history()
    future_history_id = [ID['id'] for ID in undo_history_id_list['future']]
    future_deps = []
    for hid in future_history_id:
        future_opd = OPDependency(server, projectID, hid, undo_redo='future')
        future_dependency = future_opd.mapping()
        print(f"future : {future_dependency}")
        future_deps.append(future_dependency)

    # redo step 3: rename Created_time to Created
    # redo and undo: see if the dependency changes
    redo_name = 'column-rename'
    old_name = 'Created_time'
    new_name = 'Created'
    # refineop.rename_column(old_name, new_name) # op and name dicts mapping needed
    mapping_op_name_func(server,projectID)[redo_name](old_name, new_name)
    new_history_id = refineop.get_history()
    redo_history_id = new_history_id['past'][op_step]['id']

    redo_opd = OPDependency(server, projectID,redo_history_id)
    redo_dependency = redo_opd.mapping()
    print(f"redo dependency: {redo_dependency}")
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

    get_models(project_id)
    # recipe_name = 'split_helper.json'
    # history_p = f'OpenRefineHistory/{recipe_name}'
    # load recipe from OpenRefine server
    # get_history(projectID, history_p)

    # helper(step, history_p)

    # use py-client library and apply new json


def test():

    # projectID = 2247657852239
    # server = refine.RefineServer()
    # refineop = RERineOP(server, projectID)
    # refineop.map_historyid_name()
    # history = refineop.get_history()
    # refineop.map_historyid_columns()
    # refineop.undo_project()
    # redo_id_list = [ID['id'] for ID in history['future']]
    # print(redo_id_list)
    #
    # refineop.redo_project(redo_id_list[3])


    # pprint(history)
    # id_list =[ID['id'] for ID in history['past']]
    # print(id_list)
    # mapping = refineop.map_historyid_columns()
    # print(mapping)

    # history = get_operation_history(2247657852239)
    # add_op_name = history[2]['op'].split('/')[1]
    # print(add_op_name)
    # mapping_op_dep_func()[add_op_name]()

    # name = 'test_column'
    # mapping_op_dep_func()[name]()
    #
    str1 = 'grel:cells.Mode.value + cells.Font_size.value'
    str2 = 'grel:cells[\"Font_color\"].value + cells[\"Font_size\"].value'
    # str1 = str1.split('.')
    # inputnode = (str1[1],str1[3])
    # print(inputnode)

    regex = re.findall(r"grel:cells\.(.*)\.value\s\+\scells.(.*).value", str1)
    regex2 = re.findall(r"grel:cells[\\'\'(.*)\\\'']\.value\s\+\scells[\\'\'(.*)\\\'']\.value", str2)
    print(regex2)


def test1():
    dict1 = {1:'apple'}
    dict1.update({2:'pineapple'})

    list1 =[1,3,4,5]
    list2 = [1,3,4,5,9,10]
    list3 = [1,2,4,5]
    print(list1[-1])
    # extra columns
    print(list(set(list2)-set(list1)))
    print(list(set(list3)-set(list1)))
    print(list1[::-1])
    for l in list1[::-1]:
        start = l
        print(l)


if __name__ == '__main__':
    case()