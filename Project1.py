import arcpy
import tkinter as tk
from tkinter import ttk
import pathlib
from datetime import datetime
from PIL import Image, ImageTk

import matplotlib
import matplotlib.pyplot as plt
import shapefile as shp

matplotlib.use('TkAgg')

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk
)

arcpy.env.overwriteOutput = True

pathParent = pathlib.Path(__file__).parent.resolve()
path = str(pathParent) + "\Data"

arcpy.env.workspace = path

#Inputs
tracts = "cancer_tracts.shp"
wells = "well_nitrate.shp"

#Outputs
tract_wells_join = "tract_wells.shp"
tract_wells_GWR = "GWR_tract_wells"
tract_wells_regression = "reg_tract_wells"
IDW = "IDW.tif"
outPtFeat = "IDW_Wells"
IDW_png = "IDW.png"


root = tk.Tk()
root.geometry('600x500')
root.resizable(True, True)
root.title('Project 1')

menubar = tk.Menu(root)
root.config(menu=menubar)

# create a menu
file_menu = tk.Menu(menubar, tearoff=False)

# add a menu item to the menu
file_menu.add_command(
    label='Exit',
    command=root.destroy
)


# add the File menu to the menubar
menubar.add_cascade(
    label="File",
    menu=file_menu
)

def mainMenu():
    frame = ttk.Frame(root)

    regression_button = ttk.Button(
        frame,
        text='Regression Analysis',
        command=lambda: [hide_widget(frame), regressionAnalysis()]
    )

    regression_button.pack(
        ipadx=5,
        ipady=5,
        expand=True
    )

    IDW_button = ttk.Button(
        frame,
        text='IDW Analysis',
        command=lambda: [hide_widget(frame), IDWMenu()]
    )

    IDW_button.pack(
        ipadx=5,
        ipady=5,
        expand=True
    )

    frame.pack(padx=1,pady=1)
    root.mainloop()

def hide_widget(widget): 
    widget.pack_forget() 

def regressionAnalysis():
    try:
        frame = ttk.Frame(root)

        arcpy.analysis.SpatialJoin(tracts, wells, tract_wells_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", 'GEOID10 "GEOID10" true true false 11 Text 0 0,First,#,cancer_tracts,GEOID10,0,10;canrate "canrate" true true false 6 Float 0 0,First,#,cancer_tracts,canrate,-1,-1;TARGET_FID "TARGET_FID" true true false 10 Long 0 0,First,#,well_nitrate,TARGET_FID,-1,-1;nitr_ran "nitr_ran" true true false 11 Double 0 0,Mean,#,well_nitrate,nitr_ran,-1,-1', "INTERSECT")
        #print("SpatialJoin success\n" + arcpy.GetMessages())

        arcpy.stats.GeneralizedLinearRegression(tract_wells_join, "canrate", "CONTINUOUS", tract_wells_regression, "nitr_ran")
        #print("GeneralizedLinearRegression success\n" + arcpy.GetMessages())

        results = tk.Label(frame, text=arcpy.GetMessages())
        results.pack()

        Save_button = ttk.Button(
            frame,
            text='Save Regression',
            command=lambda type = "Regression": [hide_widget(frame), Save(type, tract_wells_regression)]
        )

        Save_button.pack(
            ipadx=5,
            ipady=5,
            expand=True
        )

        View_button = ttk.Button(
            frame,
            text='View Regression',
            command=lambda type = "Regression": [hide_widget(frame), view_Files(type, tract_wells_regression)]
        )

        View_button.pack(
            ipadx=5,
            ipady=5,
            expand=True
        )
    except:
        results = tk.Label(frame, text=arcpy.GetMessages())
        results.pack()

    MM_button = ttk.Button(
        frame,
        text='Main Menu',
        command=lambda type = "Regression", mm = True: [hide_widget(frame), delete_Files(type, mm)]
    )

    MM_button.pack(
        ipadx=5,
        ipady=5,
        expand=True
    )
    
    frame.pack(padx=1,pady=1)
    

def IDWMenu():
    k_val = tk.StringVar()
    num_pts = tk.StringVar()

    frame = ttk.Frame(root)

    k_val_label = ttk.Label(frame, text="k value (k > 1):")
    k_val_label.pack(fill='x', expand=True)

    k_val_entry = ttk.Entry(frame, textvariable=k_val)
    k_val_entry.pack(fill='x', expand=True)
    k_val_entry.focus()

    num_pts_label = ttk.Label(frame, text="Number of points:")
    num_pts_label.pack(fill='x', expand=True)

    num_pts_entry = ttk.Entry(frame, textvariable=num_pts)
    num_pts_entry.pack(fill='x', expand=True)
    num_pts_entry.focus()

    custom_button = ttk.Button(frame, text="Calculate", command=lambda type ="User": [hide_widget(frame), IDWanalysis(type, k_val, num_pts)])
    custom_button.pack(fill='x', expand=True, pady=10)

    default_button = ttk.Button(
        frame,
        text='Default values',
        command=lambda type ="Default", k_val = 2, num_pts = 12: [hide_widget(frame), IDWanalysis(type, k_val, num_pts)]
    )

    default_button.pack(
        ipadx=5,
        ipady=5,
        expand=True
    )

    frame.pack(padx=1,pady=1)

def IDWanalysis(type, k_val, num_pts):
    frame = ttk.Frame(root)

    try:
        if type == "User":
            k = k_val.get()
            k = float(k)

            if k < 1:
                k = float(1)

            numPts = num_pts.get()
            numPts = str(numPts)

            if float(numPts) < 1:
                numPts = str(1)

        elif type == "Default":
            k = float(k_val)

            numPts = str(num_pts)
    except:
        k = float(2)
        numPts = str(12)


    search = "VARIABLE " + numPts

    try:
        with arcpy.EnvManager():
            out_raster = arcpy.sa.Idw(
                in_point_features=wells,
                z_field="nitr_ran",
                cell_size=0.01761631928,
                power=k,
                search_radius=search,
                in_barrier_polyline_features=None
        )
        out_raster.save(IDW)


        arcpy.sa.ExtractValuesToPoints(wells, IDW, outPtFeat, None, None)

        fields = ["nitr_ran","RASTERVALU"]

        sumErrSq = 0
        count = 0

        with arcpy.da.SearchCursor(outPtFeat,fields) as cursor:
            for row in cursor:
                # Get actual and predicted values
                testVal = row[0] 
                predVal = row[1]
                # Sum up the squred errers
                sumErrSq += (testVal - predVal) ** 2
                count += 1

        # Calculate root mean square error
        RMSE = (sumErrSq / count) ** .5

        message = "RMSE Value: " + str(f'{RMSE:.4f}') + "\nUsing k = " + str(k) + "\nAnd search = " + str(search)

        results = tk.Label(frame, text=message)
        results.pack()

        Save_button = ttk.Button(
            frame,
            text='Save IDW',
            command=lambda type = "Raster": [hide_widget(frame), Save(type, out_raster)]
        )

        Save_button.pack(
            ipadx=5,
            ipady=5,
            expand=True
        )

        View_button = ttk.Button(
            frame,
            text='View IDW',
            command=lambda type = "Raster": [hide_widget(frame), view_Files(type, out_raster)]
        )

        View_button.pack(
            ipadx=5,
            ipady=5,
            expand=True
        )

    except:
        results = tk.Label(frame, text=arcpy.GetMessages())
        results.pack()

    MM_button = ttk.Button(
        frame,
        text='Main Menu',
        command=lambda type = "Raster", mm = True: [hide_widget(frame), delete_Files(type, mm)]
    )

    MM_button.pack(
        ipadx=5,
        ipady=5,
        expand=True
    )


    frame.pack(padx=1,pady=1)

def Save(type, file):
    frame = ttk.Frame(root)

    filePath = str(pathParent) + "\SavedFiles"
    date = datetime.today().strftime('%Y-%m-%d_%H-%M-%S')

    try:
        if type == "Raster":
            fileName = "\IDW_" + date + ".tif"
            fileNamePath = filePath + fileName
            file.save(fileNamePath)
            
            mm = False
            delete_Files(type, mm)

        elif type == "Regression":
            fileName = "\Reg_" + date + ".shp"
            fileNamePath = filePath + fileName
            arcpy.conversion.ExportFeatures(file, fileNamePath)

            mm = False
            delete_Files(type, mm)
            

        message = tk.Label(frame, text="File Saved!")
        message.pack()

    except:
        message = tk.Label(frame, text="Save Failed")
        message.pack()

    MM_button = ttk.Button(
        frame,
        text='Main Menu',
        command=lambda: [hide_widget(frame), mainMenu()]
    )
    
    MM_button.pack(
        ipadx=5,
        ipady=5,
        expand=True
    )

    frame.pack(padx=1,pady=1)

def view_Files(type, file):
    frame = ttk.Frame(root)
    try:
        if type == "Raster":
            load = Image.open("data/IDW.tif").convert('RGB')

            data = load.getdata()

            new_pixel_values = []
            for pixel in data:
                if pixel == (0, 0, 0):
                    new_pixel_values.append((64, 0, 75))
                elif pixel == (1, 1, 1):
                    new_pixel_values.append((86, 30, 96))
                elif pixel == (2, 2, 2):
                    new_pixel_values.append((109, 61, 118))
                elif pixel == (3, 3, 3):
                    new_pixel_values.append((132, 92, 139))
                elif pixel == (4, 4, 4):
                    new_pixel_values.append((155, 123, 161))
                elif pixel == (5, 5, 5):
                    new_pixel_values.append((178, 154, 182))
                elif pixel == (6, 6, 6):
                    new_pixel_values.append((201, 185, 204))
                elif pixel == (7, 7, 7):
                    new_pixel_values.append((224, 216, 225))
                elif pixel == (8, 8, 8):
                    new_pixel_values.append((247, 247, 247))
                elif pixel == (9, 9, 9):
                    new_pixel_values.append((216, 224, 219))
                elif pixel == (10, 10, 10):
                    new_pixel_values.append((185, 202, 192))
                elif pixel == (11, 11, 11):
                    new_pixel_values.append((154, 179, 164))
                elif pixel == (12, 12, 12):
                    new_pixel_values.append((123, 157, 137))
                elif pixel == (13, 13, 13):
                    new_pixel_values.append((92, 135, 109))
                elif pixel == (14, 14, 14):
                    new_pixel_values.append((61, 112, 82))
                elif pixel == (15, 15, 15):
                    new_pixel_values.append((30, 90, 54))
                elif pixel == (16, 16, 16):
                    new_pixel_values.append((0, 68, 27))
                else:
                    new_pixel_values.append((0, 0, 0))

            load.putdata(new_pixel_values)

            render = ImageTk.PhotoImage(load)
            img = tk.Label(frame, image=render, bg="white")
            img.image = render
            img.pack()

            message = tk.Label(frame, text="Dark Purple - Dark Green (Low - High)")
            message.pack()

        elif type == "Regression":
            shape_path = "data/reg_tract_wells.shp"

            shapeF = shp.Reader(shape_path)

            plt.figure()
            for shape in shapeF.shapeRecords():
                x = [i[0] for i in shape.shape.points[:]]
                y = [i[1] for i in shape.shape.points[:]]
                plt.plot(x,y)
            plt.show()

            figure = Figure(figsize=(6, 4), dpi=100)

            figure_canvas = FigureCanvasTkAgg(figure, frame)

            NavigationToolbar2Tk(figure_canvas)

            figure_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        
        Save_button = ttk.Button(
            frame,
            text='Save Output',
            command=lambda: [hide_widget(frame), Save(type, file)]
        )

        Save_button.pack(
            ipadx=5,
            ipady=5,
            expand=True
        )
            
    except:
        message = tk.Label(frame, text="View Failed")
        message.pack()
        print(arcpy.GetMessages())

    MM_button = ttk.Button(
        frame,
        text='Main Menu',
        command=lambda mm = True: [hide_widget(frame), delete_Files(type, mm)]
    )

    MM_button.pack(
        ipadx=5,
        ipady=5,
        expand=True
    )

    frame.pack(padx=1,pady=1)

def delete_Files(type, mm):
    if type == "Raster":
        arcpy.management.Delete(IDW)
        arcpy.management.Delete(outPtFeat)
    elif type == "Regression":
        arcpy.management.Delete(tract_wells_join)
        arcpy.management.Delete(tract_wells_regression)

    if mm is True:
        mainMenu()
    else:
        return


if __name__ == "__main__":
    mainMenu()