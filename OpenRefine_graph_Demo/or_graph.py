from graphviz import Digraph

e = Digraph('G')

# column: Date
# counter: 0
# op: text-transform1
# expression: value.toDate()
# counter++
# structure: sequential (Date --> Date_counter Date_1)
e.attr('node', shape='box')
e.node('text-transform1')
e.node('text-transform2')
e.node('text-transform3')
e.node('text-transform5')
e.node('column-addition4')

e.attr('node',shape='ellipse')
e.node('Date', label='Date')
e.node('Date1', label='Date1')

e.node('Author', label='Author')
e.node('Author2', label='Author2')
e.node('Author3', label='Author3')
e.node('Author_Name', label='Author_Name')
e.node('Name', label='Name')
e.node('Author_Name5', label='Author_Name5')

# ops
e.edge('Date','text-transform1')
e.edge('text-transform1','Date1')
e.edge('Author','text-transform2')
e.edge('text-transform2','Author2')
e.edge('Author2','text-transform3')
e.edge('text-transform3','Author3')
e.edge('Author3','column-addition4')
e.edge('Name','column-addition4')
e.edge('column-addition4','Author_Name')
e.edge('Author_Name','text-transform5')
e.edge('text-transform5','Author_Name5')

e.view()
e.save('op')

# column: Author
# counter:1
# op: text-transform2
# expression: value.replace("@","")
# counter++
# structure: sequential (Author --> Author_counter Author_2)

# column: Author_counter Author_2
# counter:2
# op: text-transform3
# expression: value.trim()
# counter++
# structure: sequential (Author_2 --> Author_3)


# column: Author_Name
# counter:3
# op: column-addition4
# base column: Author,Name
# counter++
# structure: (Author_3,Name)--> Author_Name


# column: Author_Name
# counter:4
# op: text-transform5
# expression: value.toLowercase()
# counter++
# structure: sequential (Author_Name --> Author_Name_5)



