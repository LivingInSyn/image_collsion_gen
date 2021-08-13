from os import stat
from PIL import Image, ImageStat, ImageEnhance
import imagehash
import numpy as np
import math
import random

AVAL = 10

class DhashCollisionGen:
    BRIGHTEN = 1
    DARKEN = 2

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
    def _get_current_hash(mod_image, hash_size):
        img = mod_image.convert("L").resize((hash_size + 1, hash_size), Image.ANTIALIAS)
        pixels = np.asarray(img)
        # compute differences between columns
        diff = pixels[:, 1:] > pixels[:, :-1]
        return diff

    @staticmethod
    def _adjust_box(mode, simage):
        factor = 1.01 if mode == DhashCollisionGen.BRIGHTEN else .99
        enhancer = ImageEnhance.Brightness(simage)
        b_output = enhancer.enhance(factor)
        return b_output
    
    @staticmethod
    def _rebuild_image(width, height, boxes):
        final_img = Image.new('RGB', (width, height), 255)
        for row in boxes:
            for img in row:
                final_img.paste(img[1], img[0])
        #final_img.show()
        return final_img

    @staticmethod
    def _iterate_boxes(boxes, image_hash, width, height):
        for hrow in range(hash_size):
            for hcol in range(hash_size):
                while True:
                    c_image = DhashCollisionGen._rebuild_image(width, height, boxes)
                    current_hash = DhashCollisionGen._get_current_hash(c_image, hash_size)
                    # if the current hash and the image_hash are the same, break and continue on to the next
                    print(f'{hrow},{hcol}')
                    if not current_hash[2][4] == image_hash.hash[2][4]:
                        foo = 'a'
                    if current_hash[hrow][hcol] == image_hash.hash[hrow][hcol]:
                        break
                    # otherwise, if true - brighten the right side and try again
                    if image_hash.hash[hrow][hcol]:
                        boxes[hrow][hcol + 1][1] = DhashCollisionGen._adjust_box(DhashCollisionGen.BRIGHTEN, boxes[hrow][hcol + 1][1])
                    # else darken the right box
                    else:
                        boxes[hrow][hcol + 1][1] = DhashCollisionGen._adjust_box(DhashCollisionGen.DARKEN, boxes[hrow][hcol + 1][1])
        return boxes

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
        while True:
            boxes = DhashCollisionGen._iterate_boxes(boxes, image_hash, mod_image.width, mod_image.height)
            # recombine the boxes into a new modified image
            c_image = DhashCollisionGen._rebuild_image(mod_image.width, mod_image.height, boxes)
            current_hash = DhashCollisionGen._get_current_hash(c_image, hash_size)
            all_match = True
            for x in range(hash_size):
                if not all_match:
                    break
                for y in range(hash_size):
                    if image_hash.hash[x][y] != current_hash[x][y]:
                        print(f'mismatch at: {x},{y}')
                        all_match = False
                        break
            if all_match:
                break
        return c_image

hash_size = 8
# timage = Image.open("./with_black/timg.jpeg")
# mimage = Image.open("./with_black/mimg.jpeg")
city = Image.open("./light_photos/city.jpeg")
wedding = Image.open("./light_photos/wedding.jpeg")

collision = DhashCollisionGen.gen_collision_mod_image(city, wedding)
collision.show()
#city.convert("L").resize((hash_size + 1, hash_size), Image.ANTIALIAS).show(title='city')
#wedding.convert("L").resize((hash_size + 1, hash_size), Image.ANTIALIAS).show(title='wedding')
#collision.convert("L").resize((hash_size + 1, hash_size), Image.ANTIALIAS).show(title='collision')
image_hash = imagehash.dhash(city)
chash = imagehash.dhash(collision)
print(image_hash)
print(chash)
print(image_hash == chash)


# goodhash = imagehash.dhash(Image.open('./blue_orange.jpeg'))
# print(goodhash)
# collision = DhashCollisionGen.generate_collision(Image.open('./blue_orange.jpeg'))
# chash = imagehash.dhash(collision)
# print(chash)
# print(goodhash == chash)
