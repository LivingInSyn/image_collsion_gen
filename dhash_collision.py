from os import stat
from PIL import Image, ImageStat, ImageEnhance
import imagehash
import numpy as np
import math
import random

AVAL = 10

class DhashCollisionGen:
    @staticmethod
    def generate_collision(image, hash_size=8):
        # get the dhash of the image
        image_hash = imagehash.dhash(image, hash_size)
        iarray = np.asarray(image.convert("L").resize((hash_size + 1, hash_size), Image.ANTIALIAS))
        # build the array that'll become the colliding image
        # the first index is height, the second is the width (think y,x)
        # 0,0 is the top and left
        newimg_arr = np.zeros((hash_size, hash_size + 1))
        '''iterate through the hash'''
        # set the first element of every row to 128
        for i in range(hash_size):
            newimg_arr[i][0] = 128
        # iterate through the hash
        for hrow in range(hash_size):
            for hcol in range(hash_size):
                # if the imagehash in hrow,hcol is true, then
                if image_hash.hash[hrow][hcol]:
                    newimg_arr[hrow][hcol + 1] = newimg_arr[hrow][hcol] + AVAL
                else:
                    newimg_arr[hrow][hcol + 1] = newimg_arr[hrow][hcol] - AVAL
        timg = Image.fromarray(newimg_arr).convert("L").resize((hash_size + 1, hash_size), Image.ANTIALIAS)
        #pixels = np.asarray(timg)
        #timg.save('timg.jpeg', 'JPEG')
        return timg
    
    @staticmethod
    def _get_brightness(img):
        # c_img = np.asarray(img)
        # conv_array = np.asarray(img.convert('L'))
        # for i in range(img.size[0]):
        #     for j in range(img.size[1]):
        #         if conv_array[j][i] == 0:
        #             print(i,j, conv_array[j][i], c_img[j][i])
        img = img.convert('L')
        img = np.asarray(img).flatten()
        return np.average(img)
    
    @staticmethod
    def _handle_all_black(img):
        for _x in range(5):
            randx = random.randint(0,img.size[0])
            randy = random.randint(0,img.size[1])
            img.putpixel((randx,randy),(5,5,5))
        return img

    @staticmethod
    def _break_up_image(hash_size, mod_image):
        # w x h for size
        width = int(mod_image.width / (hash_size + 1))
        height = int(mod_image.height / hash_size)
        boxes = []
        # thanks!: https://gist.github.com/alexlib/ef7df7bfdb3dba1698f4
        for row in range(hash_size):
            boxes.append([])
            for col in range(hash_size + 1):
                #box is in left, upper, right, lower order
                box = (col*width, row*height, (col+1)*width, (row+1)*height)
                section = mod_image.crop(box)
                simg = Image.new('RGB', (width, height), 255)
                simg.paste(section)
                simg.save(f'./temp_images/{row}.{col}.jpeg')
                boxes[row].append([box,simg])
        return boxes

    @staticmethod
    def _remove_pure_black(mod_image):
        for i in range(mod_image.size[0]):
            for j in range(mod_image.size[1]):
                if mod_image.getpixel((i,j)) == ((0,0,0)):
                    mod_image.putpixel((i,j),(1,1,1))
        return mod_image

    @staticmethod
    def _get_current_hash(mod_image):
        img = mod_image.resize((hash_size + 1, hash_size), Image.ANTIALIAS)
        pixels = np.asarray(img)
        # compute differences between columns
        diff = pixels[:, 1:] > pixels[:, :-1]
        return diff

    @staticmethod
    def gen_collision_mod_image(himage, mod_image, hash_size=8):
        image_hash = imagehash.dhash(himage, hash_size)
        # crop the image up
        #mod_image.show(title='hasblack')
        #mod_image = DhashCollisionGen._remove_pure_black(mod_image)
        #mod_image.show(title='noblack')

        boxes = DhashCollisionGen._break_up_image(hash_size, mod_image)
        # for hrow in range(hash_size + 1):
        #     for hcol in range(hash_size):
        #         boxes[hrow][hcol][1].save(f"./temp_images/{hrow}.{hcol}.jpeg")
        # iterate through the hash
        for hrow in range(hash_size):
            for hcol in range(hash_size):
                print(hrow, hcol)
                lbright = DhashCollisionGen._get_brightness(boxes[hrow][hcol][1])
                rbright = DhashCollisionGen._get_brightness(boxes[hrow][hcol + 1][1])
                # right is brighter than left
                if image_hash.hash[hrow][hcol]:
                    # if right is already brighter than left, do nothing
                    if rbright > lbright:
                        continue
                    # otherwise, figure out how much to brighten the right side and then save it
                    inc_val = 0.01
                    bfactor = 1 + inc_val
                    while True:
                        enhancer = ImageEnhance.Brightness(boxes[hrow][hcol + 1][1])
                        b_output = enhancer.enhance(bfactor)
                        b_brightness = DhashCollisionGen._get_brightness(b_output)
                        if b_brightness == 0:
                            raise ValueError("Cannot brighten black, something went wrong")
                        t = ImageStat.Stat(b_output.convert('L'))
                        #b_brightness = ImageStat.Stat(b_output.convert('L')).mean[0]
                        # if the modified is brighter or equal, update the boxes val and break
                        if b_brightness >= lbright:
                            print("brightened")
                            print("pre-mod: ", lbright, rbright)
                            print("post-mod: ", lbright, b_brightness)
                            boxes[hrow][hcol + 1][1] = b_output
                            break
                        # get brighter and try again
                        bfactor = bfactor + inc_val
                else:
                    # if right is already less bright than left, do nothing
                    if rbright < lbright:
                        continue
                    # otherwise, figure out how much to darken it and then save
                    # the darkened block
                    inc_val = 0.01
                    bfactor = 1 - inc_val
                    while True:
                        enhancer = ImageEnhance.Brightness(boxes[hrow][hcol + 1][1])
                        b_output = enhancer.enhance(bfactor)
                        b_brightness = DhashCollisionGen._get_brightness(b_output)
                        if b_brightness == 0:
                            raise ValueError("Cannot make something darker than black!")
                        # if the modified is darker, update the boxes val and break
                        if b_brightness < lbright:
                            print("darkened")
                            print("pre-mod: ", lbright, rbright)
                            print("post-mod: ", lbright, b_brightness)
                            boxes[hrow][hcol + 1][1] = b_output
                            break
                        # get brighter and try again
                        bfactor = bfactor - inc_val
        # recombine the boxes into a new modified image
        # TODO: stich together
        final_img = Image.new('RGB', (mod_image.width, mod_image.height), 255)
        for row in boxes:
            for img in row:
                final_img.paste(img[1], img[0])
        #final_img.show()
        return final_img

hash_size = 8
# timage = Image.open("./with_black/timg.jpeg")
# mimage = Image.open("./with_black/mimg.jpeg")
city = Image.open("./light_photos/city.jpeg")
wedding = Image.open("./light_photos/wedding.jpeg")

collision = DhashCollisionGen.gen_collision_mod_image(city, wedding)
city.convert("L").resize((hash_size + 1, hash_size), Image.ANTIALIAS).show(title='city')
wedding.convert("L").resize((hash_size + 1, hash_size), Image.ANTIALIAS).show(title='wedding')
collision.convert("L").resize((hash_size + 1, hash_size), Image.ANTIALIAS).show(title='collision')
image_hash = imagehash.dhash(city)
chash = imagehash.dhash(collision)
print(image_hash)
print(chash)
print(image_hash == chash)


goodhash = imagehash.dhash(Image.open('./blue_orange.jpeg'))
print(goodhash)
collision = DhashCollisionGen.generate_collision(Image.open('./blue_orange.jpeg'))
chash = imagehash.dhash(collision)
print(chash)
print(goodhash == chash)
