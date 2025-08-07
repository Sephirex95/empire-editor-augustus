# -*- coding: utf-8 -*-
"""
Created on Thu Aug  7 14:51:03 2025

@author: jslaw
"""

from sg_reader import SgFileReader

reader = SgFileReader(r"Z:\C3_vanilla\C3_github_aug\C3.sg2")
images = reader.load()

print ("loaded")
# Display or save images
#for name, img_list in images.items():
   # for idx, img in enumerate(img_list):
      #  img.show()  # or img.save(f"{name}_{idx:03d}.png")
