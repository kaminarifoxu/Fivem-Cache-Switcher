# Copyright (c) 2026 GANOMABI / amiinarii.
"""Original outline icons. Self contained; no icon font or asset download required."""
from PIL import Image, ImageDraw

def draw_icon(name, color):
 im=Image.new('RGBA',(96,96)); d=ImageDraw.Draw(im); c=color; w=7
 def line(points): d.line([(x*4,y*4) for x,y in points],fill=c,width=w,joint='curve')
 def box(b,r=2): d.rounded_rectangle(tuple(v*4 for v in b),radius=r*4,outline=c,width=w)
 if name=='plus': line([(12,5),(12,19)]); line([(5,12),(19,12)])
 elif name=='play': line([(8,5),(19,12),(8,19),(8,5)])
 elif name=='check': line([(5,12),(10,17),(19,7)])
 elif name=='edit': line([(5,17),(5,20),(8,20),(20,8),(16,4),(5,17)]); line([(14,6),(18,10)])
 elif name=='trash': line([(4,7),(20,7)]); line([(7,7),(8,20),(16,20),(17,7)]); line([(9,7),(9,4),(15,4),(15,7)]); line([(10,10),(10,17)]); line([(14,10),(14,17)])
 elif name=='folder': line([(3,8),(3,20),(21,20),(21,7),(12,7),(10,4),(3,4),(3,8)]); line([(3,10),(21,10)])
 elif name=='heart': line([(12,20),(3,11),(3,7),(6,4),(9,4),(12,7),(15,4),(18,4),(21,7),(21,11),(12,20)])
 elif name=='left': line([(15,5),(8,12),(15,19)])
 elif name=='right': line([(9,5),(16,12),(9,19)])
 elif name=='external': box((3,8,16,21)); line([(10,3),(21,3),(21,14)]); line([(21,3),(10,14)])
 elif name=='servers':
  d.ellipse((12,12,84,84),outline=c,width=w); d.ellipse((32,12,64,84),outline=c,width=w); line([(3,12),(21,12)])
 elif name=='refresh':
  d.arc((16,16,80,80),45,310,fill=c,width=w); line([(19,4),(19,10),(13,10)])
 elif name=='recover': line([(8,5),(3,10),(8,15)]); line([(3,10),(14,10)]); d.arc((32,40,80,84),270,450,fill=c,width=w)
 elif name=='download': line([(12,3),(12,15)]); line([(7,10),(12,15),(17,10)]); line([(4,16),(4,21),(20,21),(20,16)])
 elif name=='grid':
  for x in (4,14):
   for y in (4,14): box((x,y,x+6,y+6),1)
 elif name=='tools': line([(5,5),(19,19)]); line([(4,7),(7,4)]); line([(6,19),(16,9)]); line([(16,9),(20,7),(20,3),(17,6),(14,3),(14,7),(16,9)])
 elif name=='info':
  d.ellipse((12,12,84,84),outline=c,width=w); line([(12,11),(12,17)]); d.ellipse((44,25,52,33),fill=c)
 return im

def make_icon(name, primary=False, danger=False):
    from customtkinter import CTkImage
    light = "#ffffff" if primary else "#b82736" if danger else "#30251e"
    dark = "#ffffff" if primary else "#e97a84" if danger else "#f0edf0"
    return CTkImage(light_image=draw_icon(name, light), dark_image=draw_icon(name, dark), size=(18, 18))
