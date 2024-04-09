import networkx as nx
import pickle
import os, sys, json
from tqdm import tqdm
import matplotlib.pyplot as plt
from urllib.parse import urlparse
import logging
from json2excel import to_excel
import argparse
import random
import socket

logging.basicConfig(level=logging.INFO,
                    filename="cluster.log",
                    format='%(asctime)s processID %(process)d [%(name)s] %(levelname)s: %(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S")

def update_connection(data, connection, fqdn, subcategory=None, attr_include_author=True):
    for line in data:
        contacts = set()
        if attr_include_author:
            contacts.add(f"author {line['author_id']}")
        try:
            for key in line['contacts']:
                if key == 'qq' or key == 'wechat' or key == 'tg' or key == 'Whatsapp' or key == 'LINE':
                    for each in line['contacts'][key]:
                        contacts.add(f"{key} {each}")
            for url in line['contacts']['websites']:
                try:
                    hostname = urlparse(url).hostname
                    if hostname not in fqdn:
                        f = socket.getfqdn(hostname)
                        if f != 'localhost':
                            fqdn[hostname] = f
                            print(f"{hostname}: {fqdn[hostname]}")
                    try:
                        contacts.add(f"websites {fqdn[hostname]}")
                    except:
                        pass
                except:
                    pass
        except Exception as e:
            pass
        for contact in contacts:
            if contact not in connection:
                connection[contact] = set()
            connection[contact].add(line['id'])
        if subcategory is not None:
            try:
                subcategory[line['sub_category']].add(line['id'])
            except:
                pass


def add_edges(connection, G, between_authors=False):
    id_contact = {}
    for node in connection:
        for id in connection[node]:
            if id not in id_contact:
                id_contact[id] = set()
            id_contact[id].add(node)
    if not between_authors:
        for u in tqdm(connection, desc='generating'):
            neighbours = set()
            for id in connection[u]:
                for v in id_contact[id]:
                    neighbours.add(v)
            for v in neighbours:
                G.add_edge(u, v)
    else:
        for attr in connection:
            for u in connection[attr]:
                for v in connection[attr]:
                    G.add_edge(f"author {u}", f"author {v}")
                    if 'connection' not in G.edges[f"author {u}", f"author {v}"]:
                        G.edges[f"author {u}", f"author {v}"]['connection'] = []
                    G.edges[f"author {u}", f"author {v}"]['connection'].append(attr)
                    
    return G
    
        
def create_cybercrime_gragh(tweet_path):
    logging.info(f'Creating a graph from cybercrime tweets...')
    
    #construct nodes and node attribute
    connection = {}
    fqdn = {}
    if os.path.exists(f"tmp_cluster/fqdn.json"):
        with open("tmp_cluster/fqdn.json", 'r') as f:
            fqdn = json.load(f)
    subcategory = {'drug': set(), 'porn': set(), 'Gambling': set(), 'surrogacy': set(), 'money-laundry': set(), 'weapon': set(), 'data_leakage': set(), 'fake_document': set(), 'harassment': set()}
    files = os.listdir(tweet_path)
    files.sort(key = lambda x: int(x[:-5]))
    for file in tqdm([os.path.join(tweet_path, each) for each in files], desc='reading tweets'):
        with open(file, 'r') as f:
            tweets = [json.loads(each) for each in f.readlines()]
        update_connection(tweets, connection, fqdn, subcategory=subcategory)
    with open("tmp_cluster/fqdn.json", 'w') as f:
        json.dump(fqdn, f)
    logging.info(f'{len(connection)} contacts')
        
    with open('tmp_cluster/subcategory.json', 'w') as f:
        json.dump({each: list(subcategory[each]) for each in subcategory}, f)
    with open('tmp_cluster/graph.json', 'w') as f:
        json.dump({each: list(connection[each]) for each in connection}, f)
    logging.info("view nodes in tmp_cluster/graph.json")
    
    #add edges and remove self-circles
    logging.info("Generating networkx Graph...")
    G = nx.Graph()
    G = add_edges(connection, G)
    for node in G.nodes:
        try:
            G.remove_edge(node, node)
        except:
            pass
            
    # save graph to file
    with open('tmp_cluster/cybercrime.pickle', 'wb') as f:
        pickle.dump(G, f)
    logging.info(f'Graph({G.number_of_nodes()} nodes and {G.number_of_edges()} edges) created and saved at tmp_cluster/cybercrime.pickle')
    return connection, subcategory, fqdn, G


def find_operators(S, fqdn, profiles):
    #S = nx.Graph()
    
    #construct node attribute
    author_ids = set()
    for node in S.nodes:
        if node.startswith('author'):
            author_ids.add(node.split(' ')[1])
    connection = {}
    profiles = [profiles[each] for each in author_ids if each in profiles]
    update_connection(profiles, connection, fqdn, attr_include_author=False)
    
    #add edges between authors and remove self-circles
    S = add_edges(connection, S, between_authors=True)
    for node in S.nodes:
        if node.startswith('author'):
            try:
                S.remove_edge(node, node)
            except:
                pass
    return S
    
    
def cluster_info(connection, S, cc_info):
    #S = nx.Graph()
    tweets = set()
    cc_info['node_count'] = S.number_of_nodes()
    cc_info['edge_count'] = S.number_of_edges()
    cc_info['contacts'] = {
        'author': 0,
        'qq': 0,
        'tg': 0,
        'wechat': 0,
        'Whatsapp': 0,
        'LINE': 0,
        'websites': 0
    }
    for node in S.nodes():
        cc_info['contacts'][node_type(node)] += 1
        for id in connection[node]:
            tweets.add(id)
    cc_info['tweet_count'] = len(tweets)
    if len(tweets) > 1:
        logging.info(cc_info)


def get_cluster_sub_type(G, subcategory, cc_info):
    #G = nx.Graph()
    tweet_ids = []
    for node in G.nodes():
        tweet_ids += connection[node]
    tweet_ids = list(set(tweet_ids))
    cc_info['subcategory'] = {}
    for id in tweet_ids:
        if id not in subcategory:
            continue
        key = subcategory[id]
        if key not in cc_info['subcategory']:
            cc_info['subcategory'][key] = 0
        cc_info['subcategory'][key] += 1
    total = sum(cc_info['subcategory'].values())
    cc_info['subcategory'] = {each: cc_info['subcategory'][each] / total for each in cc_info['subcategory']}

def get_cc_tweets(G, connection, tweet_path, user_path, savefile, cc_info):
    #G = nx.Graph()
    tweet_ids = []
    for node in tqdm(G.nodes(), desc='getting tweet ids'):
        tweet_ids += connection[node]
    tweet_ids = list(set(tweet_ids))
    tweets = []
    for file in tqdm([os.path.join(tweet_path, each) for each in os.listdir(tweet_path)], desc='reading tweets'):
        with open(file, 'r') as f:
            data = [json.loads(each) for each in f.readlines()]
            tweets += [each for each in data if each['id'] in tweet_ids]
    user_ids = set()
    for each in tweets:
        user_ids.add(each['id'])
    profiles = []
    for file in tqdm([os.path.join(user_path, each) for each in os.listdir(user_path)], desc='reading profiles'):
        with open(file, 'r') as f:
            data = [json.loads(each) for each in f.readlines()]
            profiles += [each for each in data if each['id'] in user_ids]
    for each in profiles:
        if 'ori_text' not in each:
            each['ori_text'] = each['text']
    profiles = {each['id']: {'profile_text': each['ori_text'], 'profile_contacts': each['contacts']} for each in profiles}
    
    if len(tweets) > 60000:
        tweets = random.sample(tweets, 5000)
        logging.info("Too many tweets, may exceed Excel's limit, sample out 5000 tweets")
    with open(savefile, 'w') as fs:
        for line in tweets:
            if line['id'] in profiles:
                line['profile_text'] = profiles[line['id']]['profile_text']
                line['profile_contacts'] = profiles[line['id']]['profile_contacts']
            else:
                line['profile_text'] = ''
                line['profile_contacts'] = {}
            fs.write(json.dumps(line, ensure_ascii=False)+'\n')
    to_excel(savefile, savefile.split('.')[0]+'.xlsx')
    cc_info['json_path'] = savefile
    cc_info['xlsx_path'] = savefile.split('.')[0]+'.xlsx'
    logging.info(f"View tweets in {savefile} and {savefile.split('.')[0]+'.xlsx'}")
    

def find_campaign(connection, subcategory, fqdn, G, tweet_path, user_path, dump):
    if not os.path.exists('cc_subgraph'):
        os.mkdir('cc_subgraph')
    else:
        for each in os.listdir('cc_subgraph'):
            os.remove(f'cc_subgraph/{each}')
                
    #find connected components of the graph
    logging.info(f"Looking for connected components without edges between authors...")
    cc_set = sorted(nx.connected_components(G), key=len, reverse=True)
    cc_subgraph_set = [G.subgraph(c).copy() for c in cc_set]
    logging.info(f"{len(cc_subgraph_set)} connected components are found")
        
    #dive deeper into clusters: are they from the same operator?
    cc_info = []
    profiles = read_files(user_path)
    profiles = {each['id']: each for each in profiles}
    reverse_sub = {}
    for key in subcategory:
        for id in subcategory[key]:
            reverse_sub[id] = key
    for i, S in enumerate(tqdm(cc_subgraph_set, desc='focusing on each cluster')):
        S = find_operators(S, fqdn, profiles)
        logging.info(f"subgraph{i}: {S.number_of_nodes()} nodes and {S.number_of_edges()} edges")
        tmp_info = {}
        get_cluster_sub_type(S, reverse_sub, tmp_info)
        if S.number_of_nodes() > 1:
            with open(f'cc_subgraph/{i}.pickle', 'wb') as f:
                pickle.dump(S, f)
            tmp_info['pickle_path'] = f'cc_subgraph/{i}.pickle'
            '''if i == 0:
                edges = []
                for u, v in S.edges():
                    if not u.startswith('author') or not v.startswith('author'):
                        edges.append((u, v))
                logging.info(f"subgraph0_{i}: {S.number_of_nodes()} nodes and {S.number_of_edges()} edges")
                for u, v in edges:
                    S.remove_edge(u, v)
                logging.info(f"subgraph0_{i}: {S.number_of_nodes()} nodes and {S.number_of_edges()} edges")
                sys.exit()
                biggest_cc = sorted(nx.connected_components(G), key=len, reverse=True)
                biggest_cc = [S.subgraph(c).copy() for c in biggest_cc]
                biggest_cc = [each for each in biggest_cc if each.number_of_nodes() > 1]
                logging.info(f"{len(biggest_cc)} connected components in the biggest subgraph after removing edges connected with contact-type nodes")
                for j, C in enumerate(biggest_cc):
                    logging.info(f"subgraph0_{i}: {C.number_of_nodes()} nodes and {C.number_of_edges()} edges")
                    if C.number_of_nodes() < 2000:
                        visualize(C, connection, f"cc_subgraph/0_{j}.jpg", tmp_info, with_labels=False)
                        visualize(C, connection, f"cc_subgraph/0_{j}_with_labels.jpg", tmp_info, with_labels=True)
            elif i < 100:'''
            if i > 0 and i < 100:
                if i == 15:
                    C = nx.Graph()
                    C.add_node('author 1593935063216844800')
                    C.add_node('author 1593948613675081729')
                    C.add_node('wechat SGK9527')
                    for u, v, attr in S.edges(data=True):
                        if u in C.nodes() and v in C.nodes():
                            C.add_edge(u, v)
                            if 'connection' in attr:
                                C.edges[u, v]['connection'] = attr['connection']
                    visualize(C, connection, f'cc_subgraph/{i}.jpg', tmp_info, with_labels=False)
                    visualize(C, connection, f'cc_subgraph/{i}_with_labels.jpg', tmp_info, with_labels=True)
                else:
                    visualize(S, connection, f'cc_subgraph/{i}.jpg', tmp_info, with_labels=False)
                    visualize(S, connection, f'cc_subgraph/{i}_with_labels.jpg', tmp_info, with_labels=True)
        if dump:
            get_cc_tweets(S, connection, tweet_path, user_path, f'cc_subgraph/{i}.json', tmp_info)
        cluster_info(connection, S, tmp_info)
        cc_info.append(tmp_info)
    with open("tmp_cluster/fqdn.json", 'w') as f:
        json.dump(fqdn, f)
    
    analyse(cc_info)
    return cc_info, cc_subgraph_set, profiles, fqdn


def parse_args():
    parse = argparse.ArgumentParser(description='Clustering')
    parse.add_argument('-c','--clear', action='store_true') 
    parse.add_argument('-d', '--dump', action='store_true')
    args = parse.parse_args()
    return args


def node_type(node):
    if node.startswith('author'):
        return 'author'
    elif node.startswith('qq'):
        return 'qq'
    elif node.startswith('tg'):
        return 'tg'
    elif node.startswith('wechat'):
        return 'wechat'
    elif node.startswith('websites'):
        return 'websites'
    elif node.startswith('Whatsapp'):
        return 'Whatsapp'
    elif node.startswith('LINE'):
        return 'LINE'


def visualize(G, connection, graph_save_path, cc_info, with_labels):
    #G = nx.Graph()
    logging.info(f"visualizing {graph_save_path}")
    for node in G.nodes:
        try:
            G.nodes[node]['count'] = len(connection[node])
        except Exception as e:
            print(e)
    node_colors = {
        'qq': 'blue',
        'tg': 'green',
        'wechat': 'cyan',
        'Whatsapp': 'magenta',
        'LINE': 'yellow',
        'websites': 'purple',
        'author': 'red'
    }
    node_color_list = [node_colors[node_type(node)] for node in G.nodes()]
    edge_colors = {
        True: 'red',
        False: 'black'
    }
    edge_color_list = [edge_colors['connection' in data] for _, _, data in G.edges(data=True)]
    node_size_list = [data['count']*100 for _, data in G.nodes(data=True)] 
    plt.figure(figsize=(50, 50)) 
    nx.draw(G, with_labels=with_labels, node_color=node_color_list, node_size=node_size_list, edge_color=edge_color_list)
    node_colors = {
        'QQ': 'blue',
        'Telegram': 'green',
        'WeChat': 'cyan',
        'Whatsapp': 'magenta',
        'LINE': 'yellow',
        'websites': 'purple',
        'author': 'red'
    }
    legend_handles = [plt.Line2D([0], [0], marker='o', color='w', label=node_type, markerfacecolor=color, markersize=100) for node_type, color in node_colors.items()]
    plt.legend(handles=legend_handles, loc='best', prop={'size': 100})
    plt.savefig(graph_save_path)
    plt.close('all')
    cc_info['jpg_path'] = graph_save_path
    logging.info(f"graph jpg saved at {graph_save_path}")
    
    
def read_files(path):
    data = []
    for file in tqdm([os.path.join(path, each) for each in os.listdir(path)], desc=f'reading {path}'):
        with open(file, 'r') as f:
            data += [json.loads(each) for each in f.readlines()]
    logging.info(f"{len(data)} lines of data")
    return data
    
    
def analyse(cc_info):
    contact_count = {}
    singleton = []
    for each in cc_info:
        con = sum(list(each['contacts'].values())) - each['contacts']['author']
        if con not in contact_count:
            contact_count[con] = 0
        contact_count[con] += 1
        if con == 0:
            singleton.append(each)
    logging.info(f"(number of contacts, number of clusters embedding this number of contacts)")
    logging.info(sorted(contact_count.items(), key = lambda kv:(kv[1], kv[0])))
    total = sum(list(contact_count.values()))
    contact_count = {each: contact_count[each]/total for each in contact_count}
    logging.info(sorted(contact_count.items(), key = lambda kv:(kv[1], kv[0])))
    total_tweets = sum([each['tweet_count'] for each in cc_info])
    singleton_tweets = sum([each['tweet_count'] for each in singleton])
    total_accounts = sum([each['contacts']['author'] for each in cc_info])
    singleton_accounts = sum([each['contacts']['author'] for each in singleton])
    logging.info(f"Singletons take up {len(singleton)/len(cc_info)} of all clusters, {singleton_tweets/total_tweets} of all tweets, {singleton_accounts/total_accounts} of all accounts")
    
    single_account_clusters = [each for each in cc_info if each['contacts']['author'] == 1 and sum(list(each['contacts'].values())) > each['contacts']['author']]
    total_contacts = sum([sum(list(each['contacts'].values())) - each['contacts']['author'] for each in cc_info])
    mis_extracted_contacts = sum([sum(list(each['contacts'].values())) - each['contacts']['author'] for each in single_account_clusters])
    logging.info(f"{len(single_account_clusters)} clusters({len(single_account_clusters)/len(cc_info)}) have only one author-type node but have at least 1 contact node, taking up {mis_extracted_contacts/total_contacts} of all contacts")
    
    category_count = {}
    for each in cc_info:
        cat = len(each['subcategory'])
        if cat not in category_count:
            category_count[cat] = 0
        category_count[cat] += 1
    logging.info(f"(number of subcategory, number of clusters involving this number of subcatogory)")
    logging.info(sorted(category_count.items(), key = lambda kv:(kv[1], kv[0])))
    total = sum(list(category_count.values()))
    category_count = {each: category_count[each]/total for each in category_count}
    logging.info(sorted(category_count.items(), key = lambda kv:(kv[1], kv[0])))
    
    
def across_campaign(subgraphs, profiles, fqdn):
    G = nx.Graph()
    connection = {}
    profiles = [profiles[each] for each in profiles if 'contacts' in profiles[each]]
    for i, S in enumerate(subgraphs[1:]):
        ids = [each.split(' ')[1] for each in S.nodes() if each.startswith('author')]
        contacts = [profiles[each]['contacts'] for each in profiles if each in ids]
        if len(contacts) > 0:
            print(len(contacts))
        tmp = set()
        for each in contacts:
            for key in each:
                if key != 'websites':
                    for con in each[key]:
                        tmp.add(f"{key} {con}")
                else:
                    for url in each[key]:
                        hostname = urlparse(url).hostname
                        if hostname in fqdn:
                            tmp.add(f"{key} {fqdn[hostname]}")
        for each in tmp:
            if each not in connection:
                connection[each] = set()
            connection[each].add(i)
    for con in connection:
        for u in connection[con]:
            for v in connection[con]:
                if G.has_edge(u, v):
                    G.edges[u, v]['contacts'].append(con)
                else:
                    G.add_edge(u, v, {'contacts': [con]})
    cc_set = sorted(nx.connected_components(G), key=len, reverse=True)
    cc_subgraph_set = [G.subgraph(c).copy() for c in cc_set]
    cc_subgraph_set = [each for each in cc_subgraph_set if each.number_of_nodes() > 1]
    logging.info(f"{len(cc_subgraph_set)} connected components found in across_campaign")
    for i, S in enumerate(cc_subgraph_set):
        plt.figure(figsize=(100, 100)) 
        node_colors = {'campain': 'black'}
        nx.draw(G, with_labels=True, node_color='black')
        legend_handles = [plt.Line2D([0], [0], marker='o', color='w', label=node_type, markerfacecolor=color, markersize=100) for node_type, color in node_colors.items()]
        plt.legend(handles=legend_handles, loc='upper right', prop={'size': 100})
        plt.savefig(f"cc_subgraph/across_campaign_{i}.jpg")
        plt.close('all')
        logging.info(f"graph jpg saved at cc_subgraph/across_campaign_{i}.jpg")
    

if __name__ == '__main__':  
    logging.info('')
    tweet_path = '/data/hongyuwang/data/CP/splited_tweets'
    user_path = '/data/hongyuwang/data/CP/splited_users'
    
    #test
    '''with open('graph.json', 'r') as f:
        connection = json.load(f)
    for i in reversed(range(10)):
        with open(f'cc_subgraph/{i}.pickle', 'rb') as f:
            G = pickle.load(f)
        logging.info("visualizing")
        logging.info(f"{G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
        visualize(G, connection, f'cc_subgraph/{i}.jpg', {})
    sys.exit()'''
    #test
    
    args = parse_args()
    if args.clear:
        if not os.path.exists('tmp_cluster'):
            os.mkdir('tmp_cluster')
        logging.info('Clear previous results: cc_subgraph/*')
        connection, subcategory, fqdn, G = create_cybercrime_gragh(tweet_path)
    else:
        with open('tmp_cluster/graph.json', 'r') as f:
            connection = json.load(f)
        with open(f'tmp_cluster/cybercrime.pickle', 'rb') as f:
            G = pickle.load(f)
        with open('tmp_cluster/subcategory.json', 'r') as f:
            subcategory = json.load(f)
        with open('tmp_cluster/fqdn.json', 'r') as f:
            fqdn = json.load(f)

    cc_info, subgraphs, profiles, fqdn = find_campaign(connection, subcategory, fqdn, G, tweet_path, user_path, dump=args.dump)
    
    #across_campaign(subgraphs, profiles, fqdn)
    
    logging.info("Finished.")