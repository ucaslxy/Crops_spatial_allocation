# -*- coding: utf-8 -*-
"""
Created on Mon Oct 24 10:30:43 2022

@author: User
"""
from osgeo import gdal
import numpy as np
import pandas as pd

def read_img(filename):
    dataset=gdal.Open(filename)

    im_width = dataset.RasterXSize
    im_height = dataset.RasterYSize
    im_bands = dataset.RasterCount

    im_geotrans = dataset.GetGeoTransform()
    im_proj = dataset.GetProjection()
    im_data = dataset.ReadAsArray(0,0,im_width,im_height)

    del dataset 

    return im_proj,im_geotrans,im_data



def write_img(filename,im_proj,im_geotrans,im_data):
    if 'int8' in im_data.dtype.name:
        datatype = gdal.GDT_Byte
    elif 'int16' in im_data.dtype.name:
        datatype = gdal.GDT_UInt16
    else:
        datatype = gdal.GDT_Float32

    if len(im_data.shape) == 3:
        im_bands, im_height, im_width = im_data.shape
    else:
        im_bands, (im_height, im_width) = 1,im_data.shape 

    driver = gdal.GetDriverByName("GTiff")
    dataset = driver.Create(filename, im_width, im_height, im_bands, datatype)
    dataset.SetGeoTransform(im_geotrans)
    dataset.SetProjection(im_proj)

    if im_bands == 1:
        dataset.GetRasterBand(1).WriteArray(im_data)
    else:
        for i in range(im_bands):
            dataset.GetRasterBand(i+1).WriteArray(im_data[i])
    del dataset


# processing order
crops_path = "D:/CDL_crops_30s/CDL_"    # the CDL data path, absolute path, e.g., D:/CDL/...
crops_outpath = "D:/Crop_harv/Crop_harv_" # the out path, absolute path, e.g., D:/CDL/...
crops = ['Corn', 'Soybean', 'Hay', 'Wwheat', 'Swheat', 'Cotton', 'Sorghum',
         'Rice', 'Barley','Peanuts', 'Sunflower', 'Sugarbeet', 'Potato', 
         'Oat', 'Millit', 'Tobacco', 'Flaxseed', 'Rye', 'Sweetpotato', 
         'Buckwheat', 'Rapeseed']


crop_harv_file = "crops_harvested.xlsx" # the crops harvest area, absolute path, e.g., D:/CDL/...

crop_harv = np.zeros([92, 10, 21])   # county numbers, total years, crop types
# if you want to run CONUS, please change 92 to the amonut of all counties in CONUS
# if you want to run more than one hundred years, please change 10 to the years (e.g., 150)
# if you want to run several crop types, plese change 21 to another number


for cid in range(len(crops)):
    crop_harv_pd = pd.read_excel(crop_harv_file, sheet_name=crops[cid], engine='openpyxl')
    crop_harv_np = crop_harv_pd.to_numpy()
    crop_harv[:, :, cid] = crop_harv_np[662:754, 5:15]
    
# if you want to run CONUS, pleae change 662:754 to 1:; 5:15 to 5:
# The above index is related to your crop harv. file

county_id = crop_harv_np[662:754, 0]  # see above comments
crop_harv[np.isnan(crop_harv)] = 0

im_proj,im_geotrans, mask_id = read_img("county_id.tif")

# you need create an couny id mask based on the county GEOID value or FIPS value

row = mask_id.shape[0]
col = mask_id.shape[1]

# total years
baseyr = 1850 # just an example, please change it according to your run
yrs = 10     # total years you want to simulate
ct_num = 92  # county numbers, please change it to the county amount if you want run CONUS
for yr in range(yrs):
    print(yr)
    max_frac_g = np.zeros([row, col])
    max_frac_g = max_frac_g + 1.0
    for cid in range(len(crops)):
        print(crops[cid])
        crop_frac = np.zeros([row, col])
        im_proj,im_geotrans, cdl_crop = read_img(crops_path + crops[cid] + ".tif")
        for ctid in range(ct_num):
            print(ctid)
            ct_loc = np.where(mask_id == county_id[ctid])
            ct_cdl = cdl_crop[ct_loc[0][:], ct_loc[1][:]]
            max_frac = max_frac_g[ct_loc[0][:], ct_loc[1][:]]
            ct_area = ct_loc[0].shape[0] * 1.0
            ct_harv = crop_harv[ctid, yr, cid]
            target_frac = ct_harv * 0.00405 / ct_area
            print(target_frac)
            demand_frac = target_frac
            ct_cdl_mean = np.mean(ct_cdl)
            if (ct_cdl_mean < 0.00000001) | (ct_harv == 0):
                crop_frac[ct_loc[0][:], ct_loc[1][:]] = 0
            else:
                for ir in range(100):
                    tmp = target_frac * ct_cdl / ct_cdl_mean
                    tmp = np.where(tmp < max_frac, tmp, max_frac)
                    tmp = np.where(tmp < 0.00001, 0, tmp)
                    if ir == 0:
                        tmp_target = tmp
                    else:
                        tmp_target = tmp_target + tmp
                    tmp_target = np.where(tmp_target < max_frac, tmp_target, max_frac)
                    tmp_dif = (demand_frac - np.mean(tmp_target)) * ct_area/1000.0
                    if (tmp_dif <= 0.01) | (ir == 99):
                        crop_frac[ct_loc[0][:], ct_loc[1][:]] = tmp_target
                        break
                    else:
                        target_frac = target_frac - np.mean(tmp_target)
            
        max_frac_g = max_frac_g - crop_frac
        outName = crops_outpath + crops[cid] + "_" + str(yr + baseyr) + ".tif"
        write_img(outName,im_proj,im_geotrans,crop_frac)
            
        
        
        
