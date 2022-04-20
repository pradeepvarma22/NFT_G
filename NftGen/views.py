from django.shortcuts import render,redirect
from NftGen.models import User
import PIL
from django.http import HttpResponse,HttpResponseRedirect
from django.http import FileResponse
from django.urls import reverse
from NftGen.models import Image,LayersModel, ProjectDesc
from .forms import ProjRegistration
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
from utility.nftstorage import NftStorage
from utility.pinata import Pinata

from shutil import make_archive
from wsgiref.util import FileWrapper
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from random import choices
from random import seed
from os import PathLike
from typing import Union
import subprocess

import os
import json
import zipfile
import glob
import shutil
from API_KEYS.keys import keys

#print(keys)

layer_cnt = 1
rand_seed = 345698135
base_uri = "ipfs://"
NFTSTORAGE_API_KEY = keys['NFTSTORAGE']
PINATA_JWT = keys['PINATA']

#project_name= "Test_Pro"

img_file_list = [] 
meta_file_list = []
gen_imgs = {}

# Create your views here.
def loginView(request):
    if request.POST:
        walletAddress=request.POST.get('address')
        user = User.objects.get_or_create(walletAddress = walletAddress)
        user.save()
        request.session['walletAddress'] = walletAddress
        return redirect('home')

    else:
        return render(request,'login.html')


def Home(request):

    context = {
        'moralisId':request.session.get('moralisAddress'),
        'walletAddress':request.session.get('walletAddress')
    }
    return render(request,'home.html',context)




def add_proj(request):
    tuser=User.objects.get(walletAddress=request.session.get('walletAddress'))
    temp = ProjectDesc()
    temp.user = tuser
    temp.proj_name = request.POST.get('projname')
    temp.total = request.POST.get('total')
    LayerData = LayersModel.objects.filter(user=tuser)

    context = { 'proj':temp.proj_name,'total':temp.total }
    temp.save()
    return HttpResponseRedirect(reverse(('LayerGet'),kwargs=context))

def uploadnft(request):
    nstorage = {}
    tuser=User.objects.get(walletAddress=request.session.get('walletAddress'))
    c = NftStorage(NFTSTORAGE_API_KEY)
    po = ProjectDesc.objects.get(user=tuser)
    proj_name= po.proj_name
    print('-----')
    print(proj_name)
    """
    files = []
    for i in img_file_list:
        files.append(('file', (i.split('/')[2], open(i, 'rb').read(), 'image/png')))
    print(files)
    """

    # upload images 
    print(img_file_list)
    cid = c.upload(img_file_list, 'image/png')
    po.img_hash = cid
    nstorage['image_directory_cid'] = cid
    print(nstorage['image_directory_cid'])
    # update Metadata with CID
    update_meta_cid(meta_file_list, cid)
    
    # upload
    print(meta_file_list)
    cid = c.upload(meta_file_list, 'application/json')
    po.meta_hash = cid
    nstorage['metadata_directory_cid'] = cid
    print(nstorage['metadata_directory_cid'])
    po.save()
    p = Pinata(PINATA_JWT)
    for k, v in nstorage.items():
        name = proj_name + ' ' + k.split('_')[0]
        p.pin(name, v)

    stats = generate_mint_stats(gen_imgs, f('./images'))
    context = {
        "stats": stats,
    }
    return render(request, "json_output.html", context)


def update_meta_cid(file, cid):
    for i in file:
        with open(i) as f:
             data = json.load(f)
             img_file = data['image'].replace(base_uri, '')
             data['image'] = base_uri + cid + '/' + img_file
        
        with open(i, 'w') as outfile:
            json.dump(data, outfile, indent=4)    



def generate_mint_stats(all_images, mapping):
    stats = {}

    keys = [i.split("-")[1] for i in mapping.keys()]
    values = [i for i in mapping.values()]

    for x in range(0, len(keys)):
        tmp = {}
        for y in range(0, len(values[x])):
            img_c = {values[x][y]: 0}
            tmp.update(img_c)
        stats[keys[x]] = tmp

    for k, v in all_images.items():
        img_key = [i.split("-")[1] for i in v.keys()]
        img_values = [i for i in v.values()]

        for x in range(0, len(img_key)):
            stats[img_key[x]][img_values[x]] += 1

    with open('./mint_stats', 'w') as outfile:
        json.dump(stats, outfile, indent=4)

    json_pretty = json.dumps(stats, sort_keys=True, indent=4)

    return json_pretty
    

def homeView(request):
    return render(request,'index.html')


def setrarity(request,k):
    img_obj = Image.objects.get(id = k)
    img_obj.rarity = request.POST.get('rarity')
    img_obj.save()
    return HttpResponseRedirect(reverse('LayerGet'))


def LayerGet(request):

    mainuser = User.objects.get(walletAddress=request.session.get('walletAddress'))
    tuser=User.objects.get(walletAddress=mainuser)
    layoutDataF = LayersModel.objects.filter(user=tuser)
    imagesObjects = Image.objects.filter(user=tuser)
    t =1 
    for l in layoutDataF:
        t *= int(l.img_num)
    d = f('.\images')
    print(d)
    context={'layoutDataV':layoutDataF,'imagesObjects':imagesObjects, 'max':t}
    return render(request,'layout.html',context)


def LayerPost(request):

    global layer_cnt
    mainuser = User.objects.get(walletAddress=request.session.get('walletAddress'))
    tuser=User.objects.get(walletAddress=mainuser)
    tlayout = request.POST.get('layoutVariable')
    temp = LayersModel()
    temp.user = tuser
    temp.layer_name = str(layer_cnt) +'-'+ tlayout
    temp.save()
    layer_cnt += 1
    return redirect('LayerGet')


def uploadImage(request,pkk):
    mainuser = User.objects.get(walletAddress=request.session.get('walletAddress'))
    tuser=User.objects.get(walletAddress=mainuser)
    files = request.FILES.getlist('allimages')  
    img_num = len(files)
    #fss = FileSystemStorage()
    #print(list(files))
    tLayer = LayersModel.objects.get(id=pkk)
    tLayer.img_num = str(img_num)
    tLayer.save()
    index = 1
    for f in files:
        a = Image()
        a.layer = tLayer
        a.user = tuser
        #a.name = f.name
        a.image = f
        a.save()
        index+=1
    
    return redirect('LayerGet')

   
def GenerateImg(request):
    mainuser = User.objects.get(walletAddress=request.session.get('walletAddress'))
    tuser=User.objects.get(walletAddress=mainuser)
    layoutDataF = LayersModel.objects.filter(user=tuser)
    po = ProjectDesc.objects.get(user=request.user)
    print(po.proj_name)
    tot = po.total
    tot = int(tot)
    proj = po.proj_name
    global gen_imgs
    td = {}
    d = f('.\images')
    td ={}
    for l in layoutDataF:
        imagesObjects = Image.objects.filter(layer=l)
        #print(imagesObjects)
        l = str(l)
        td[l] = []
        
        for i in imagesObjects:
            #print(i.rarity)
            td[l].append(float(i.rarity))
    #print(d)
    #print(td)
    #get_random_selection(d,td)
    images = {}
    for x in range(1, tot+1):
        dup_image_check = True
        image = {}
        seed(x+rand_seed)
        
        # cycle through attributes and check for uniqueness
        counter = 1
        while dup_image_check:
            output = get_random_selection(d,td)
            if len(images) == 0:
                # this is the first NFT. Skip dup check
                dup_image_check = False
            else:
                checker = list(images.values())
                if output in checker:
                    # duplicate - update seed and reselect
                    seed(rand_seed-x-counter)
                    counter += 1
                else:
                    # not a duplicate
                    dup_image_check = False
        
        image[x] = output
        images.update(image)
    
    gen_imgs = images
    generate_image_helper(images,proj)
    return redirect('LayerGet')


def f(path):

    d ={}
    dirs = sorted([f for f in os.listdir(path) if not f.startswith('.')])
    for i in dirs:
        sub_dir = os.path.join(path, i)
        files = sorted([f for f in os.listdir(sub_dir) if not f.startswith('.')])
        d[i] = [s.replace(".png", "") for s in files]
    return d


def get_random_selection(attributes,rarity):
    temp = {}
    for i in attributes.keys():
        # get values
        values = attributes[i]
        # get rarity weighting
        weights = rarity[i]
        selection = choices(values, weights)
        # add selection
        temp.update({i: selection[0]})
    return temp


def generate_image_helper(all_images,project_name):

    file_list = []
    global img_file_list
    global meta_file_list
    path = BASE_DIR + '/output'
    img_path = path+'/images'
    meta_path = path+'/metadata'
    try:
        os.mkdir(path)
    except:
        pass
    try:
        os.mkdir(img_path)
    except:
        pass
    try:
        os.mkdir(meta_path)
    except:
        pass
    
    # get images
    for k, v in all_images.items():
        meta = []
        directories = [i for i in v.keys()]
        imgnames = [i for i in v.values()]
        print(directories)
        print(imgnames)
        for x in range(0, len(directories)):
            att = {"trait_type": directories[x].split("-")[1],
                   "value": imgnames[x]}
            meta.append(att)

        # if only 2 images to combine - single pass
        if len(v) <= 2:
            im1 = PIL.Image.open(f'./images/{directories[0]}/{imgnames[0]}.png').convert('RGBA')
            im2 = PIL.Image.open(f'./images/{directories[1]}/{imgnames[1]}.png').convert('RGBA')
            com = PIL.Image.alpha_composite(im1, im2)
        # if > 2 images to combine - multi pass
        else:
            im1 = PIL.Image.open(f'./images/{directories[0]}/{imgnames[0]}.png').convert('RGBA')
            im2 = PIL.Image.open(f'./images/{directories[1]}/{imgnames[1]}.png').convert('RGBA')
            com = PIL.Image.alpha_composite(im1, im2)
            counter = 2
            while counter < len(v):
                im = PIL.Image.open(f'./images/{directories[counter]}/{imgnames[counter]}.png').convert('RGBA')
                com = PIL.Image.alpha_composite(com, im)
                counter += 1
        
        #path = os.path.join(BASE_DIR, directory) 
        # save image
        rgb_im = com.convert('RGB')
        file = img_path+"/"+ str(k) + ".png"
        img_file_list.append(file)
        rgb_im.save(file)  

        # save metadata
        token = {
            "image": base_uri + str(k) + '.png',
            "tokenId": k,
            "name": project_name + ' ' + "#" + str(k),
            "attributes": meta
        }

        meta_file = meta_path+"/" + str(k) + '.json'
        meta_file_list.append(meta_file)
        with open(meta_file, 'w') as outfile:
            json.dump(token, outfile, indent=4)
    
    make_gif(img_path)
    #subprocess.call(['chmod', '0o777', path])
    try:
        zip_dir(path,'result')
    except:
        pass
    

def zip_dir(dir: Union[Path, str], filename: Union[Path, str]):
    """Zip the provided directory without navigating to that directory using `pathlib` module"""

    # Convert to Path object
    dir = Path(dir)

    with zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for entry in dir.rglob("*"):
            zip_file.write(entry, entry.relative_to(dir))


def download(request):

    path_to_file = BASE_DIR + '/result'
    zip_file = open(path_to_file, 'rb')
    response = HttpResponse(zip_file, content_type='application/force-download')
    response['Content-Disposition'] = 'attachment; filename="%s"' % 'results.zip'
    return response

def make_gif(frame_folder):

    frames = [PIL.Image.open(image) for image in glob.glob(f"{frame_folder}/*.PNG")]
    frame_one = frames[0]
    frame_one.save("./output/my_awesome.gif", format="GIF", append_images=frames,
               save_all=True, duration=100, loop=0)
