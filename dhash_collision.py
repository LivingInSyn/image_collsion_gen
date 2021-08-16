from os import stat
from PIL import Image, ImageStat, ImageEnhance
import imagehash
import numpy as np
import argparse
import sys
import math

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
                # setting right makes sure we don't lose pixels off the right side as we rebuild
                right = (col+1)*width if col != hash_size else mod_image.width
                left = col*width
                box_width = right - left
                # setting lower makes sure we don't lose pixels off the bottom
                lower = (row+1)*height if row != (hash_size - 1) else mod_image.height
                upper = row*height
                box_height = lower - upper
                #box is in left, upper, right, lower order
                box = (left, upper, right, lower)
                section = mod_image.crop(box)
                simg = Image.new('RGB', (box_width, box_height), 255)
                simg.paste(section)
                # simg.save(f'./temp_images/{row}.{col}.jpeg')
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
                # (image, box)
                final_img.paste(img[1], img[0])
        #final_img.show()
        return final_img

    @staticmethod
    def _iterate_boxes(boxes, image_hash, width, height):
        for hrow in range(len(image_hash)):
            for hcol in range(len(image_hash)):
                while True:
                    c_image = DhashCollisionGen._rebuild_image(width, height, boxes)
                    current_hash = DhashCollisionGen._get_current_hash(c_image, len(image_hash))
                    # if the current hash and the image_hash are the same, break and continue on to the next
                    print(f'{hrow},{hcol}')
                    if current_hash[hrow][hcol] == image_hash[hrow][hcol]:
                        break
                    # otherwise, if true - brighten the right side and try again
                    if image_hash[hrow][hcol]:
                        boxes[hrow][hcol + 1][1] = DhashCollisionGen._adjust_box(DhashCollisionGen.BRIGHTEN, boxes[hrow][hcol + 1][1])
                    # else darken the right box
                    else:
                        boxes[hrow][hcol + 1][1] = DhashCollisionGen._adjust_box(DhashCollisionGen.DARKEN, boxes[hrow][hcol + 1][1])
        return boxes

    @staticmethod
    def gen_collision_mod_image(image_hash, mod_image, hash_size=8):
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
                    if image_hash[x][y] != current_hash[x][y]:
                        print(f'mismatch at: {x},{y}')
                        all_match = False
                        break
            if all_match:
                break
        return c_image
    
    @staticmethod
    def get_hash_array(hash):
        scale = 16 ## equals to hexadecimal
        num_of_bits = 8
        binary = bin(int(hash, scale))[2:]
        binary = binary.zfill(len(binary) + (8 - (len(binary)%8)))
        if len(binary)%8 != 0:
            raise ValueError("invalid hash size")
        hash_size = math.sqrt(len(binary))
        # make sure it's a perfect square
        if int(hash_size + 0.5) ** 2 != len(binary):
            raise ValueError('invalid hash size')
        hash_size = int(hash_size)
        # split into an actual binary array
        binary = [int(i) for i in binary]
        binary = list(map(bool,binary))
        binary = np.array(binary)
        binary = binary.reshape(hash_size, hash_size)
        return binary

city = Image.open("./light_photos/city.jpeg")
print(imagehash.dhash(city))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create a dHash collision.')
    parser.add_argument('-s', '--hash-size', type=int, default=8, help='the dHash hash size. This is ignored with the -t arg.')
    parser.add_argument('-c','--collision-target', help='path to the image to create a collision with')
    parser.add_argument('-t','--collision-hash', help='the hash of an image to create a collision with')
    parser.add_argument('mod_image', help='path to the image to be modified')
    parser.add_argument('image_out', help='path to write the modified image to')
    args = parser.parse_args()
    print(args)
    # make sure we have either -c or -t and not both
    if not args.collision_target and not args.collision_hash:
        print("please select -c or -t")
        sys.exit(1)
    if args.collision_target and args.collision_hash:
        print("Please select -c or -t, not both!")
        sys.exit(1)
    if args.collision_target:
        # check hash_size
        if not args.hash_size or args.hash_size < 4:
            print("Hash size must be an integer > 4")
            sys.exit(1) 
        image = Image.open(args.collision_target)
        image_hash = imagehash.dhash(image, args.hash_size)
        mod_image = Image.open(args.mod_image)
        collision_image = DhashCollisionGen.gen_collision_mod_image(image_hash.hash, mod_image, args.hash_size)
        c_hash = imagehash.dhash(collision_image, args.hash_size)
        a = np.array_equal(image_hash.hash, c_hash.hash)
        collision_image.save(args.image_out)
    else:
        hash_array = DhashCollisionGen.get_hash_array(args.collision_hash)
        collision_image = DhashCollisionGen.gen_collision_mod_image(hash_array, args.mod_image, len(hash_array))
        collision_image.save(args.image_out)
