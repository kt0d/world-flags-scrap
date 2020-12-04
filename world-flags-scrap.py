from bs4 import BeautifulSoup
import requests
import shutil
import pathlib
import json
import unicodedata
from multiprocessing import Pool
import functools

LINK='https://world-flags.org/'
BASEDIR='output'
FROM, TO = None, None

def save_image(link, path):
    print('Downloading image:\t', link)
    r = requests.get(link, stream=True)
    if r.status_code != 200:
        print('Failed to download image')
        return
    with path.open(mode='wb') as f:
        r.raw.decode_content = True
        shutil.copyfileobj(r.raw, f)        

def save_json(data, path):
    with path.open(mode='w') as f:
        json.dump(data, f, ensure_ascii=False, indent=0)

def get_soup(link):
    print('Downloading page:\t', link)
    p = requests.get(link)
    if p.status_code != 200:
        print('Failed to download page')
        return
    return BeautifulSoup(p.text, 'lxml')

def string_array(strs):
    stripped = ''.join(strs).lstrip().rstrip()
    return unicodedata.normalize('NFKD', stripped).replace('\r', '').split('\n')

def get_pics(content, dirpath, prefix):
    front_img = content.find('div', class_='front').img['src']
    back_img = content.find('div', class_='back').img['src']
    threeview = content.find_all('div', class_='ch_support_item_con')[2].img
    if threeview is not None:
        save_image(threeview['src'], dirpath.joinpath(f'{prefix}3view.png'))

    save_image(front_img, dirpath.joinpath(f'{prefix}front.png'))
    save_image(back_img, dirpath.joinpath(f'{prefix}back.png'))

def parse_character(link, basedir, with_pics, with_json,structured=False):
    country = link.split('/')[-1].split('.')[0]
    region = link.split('/')[-2]

    dirpath = pathlib.Path(basedir)
    prefix = ''
    if structured:
        dirpath = dirpath.joinpath(country)
    else:
        prefix = country + '_'
    dirpath.mkdir(parents=True, exist_ok=True)

    s = get_soup(link)
    content = s.find('div', class_='p_content')
    
    if with_pics:
        get_pics(content, dirpath, prefix)

    if not with_json:
        return

    info = {}
    info['country'] = country
    info['region'] = region
    info['desc'] = content.find('p', class_='ch_desc_txt').string
    info['nick'] = content.find('p', class_='ch_mark_nik').string
    info['cv'] = list(content.find('p',class_='ch_txt_tl').stripped_strings)[1]

    props = list(content.find('div', class_='ch_props').find_all('p', class_='ch_txt_tl'))
    prop_dict = {
            0: 'birthday',
            1: 'height',
            2: 'bloodtype',
            3: 'hobby',
            4: 'special skill',
            5: 'bad at',
            6: 'favorite food',
            }
    for idx, name in prop_dict.items():
        try:
            info[name] = list(props[idx].strings)[1]
        # some samurai don't have all properties specified
        except IndexError:
            info[name] = None

    personality = content.find_all('div', class_='ch_support_item_con')[1].strings
    info['personality'] = string_array(personality)
    about = content.find('p', class_='p_desc_item_con').strings
    info['about'] = string_array(about)

    tag_link = s.find('a', class_='pagi_item_back')['href']
    info['tag'] = tag_link.rpartition('/')[2].partition(';')[0]

    save_json(info, dirpath.joinpath(country).with_suffix('.json'))

def scrap(link, start, end):
    soup = get_soup(link)
    character_list = soup.find('ul', id='characters_sp').find_all('li')
    character_links = [x.a['href'] for x in character_list]
    character_links = character_links[start:end]
    
    i = (start or 0) + 1
    total_count = len(character_links)
    print('Found', total_count, 'characters')
    parse = functools.partial(parse_character, basedir=BASEDIR, with_pics=True, with_json=True)
    
    with Pool(8) as p:
        p.map(parse, character_links)

if __name__ == "__main__":
    try:
        scrap(LINK, FROM, TO)
    except KeyboardInterrupt:
        print('Exiting...')
