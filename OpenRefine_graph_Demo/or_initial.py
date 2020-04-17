from graphviz import Digraph
# project id: 2014260363969
e = Digraph()

e.attr('node', shape='ellipse')
e.node('Date(CST)')
e.node('Author')
e.node('Name')
e.node('Country')
e.node('State/Region')
e.node('City/Urban Area')

e.attr('node', shape ='box')
e.node('create project')
e.edge('filename','create project')

e.edge('create project','Date(CST)')
e.edge('create project','Author')
e.edge('create project','Name')
e.edge('create project','Country')
e.edge('create project','State/Region')
e.edge('create project','City/Urban Area')

e.view()
e.save('init')


