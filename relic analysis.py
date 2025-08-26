
import wx

class Relics:
    def __init__(self, main, sub1, sub2, sub3, sub4):
        self.main = main
        self.sub1 = sub1
        self.sub2 = sub2
        self.sub3 = sub3
        self.sub4 = sub4
    def __str__(self):
        return f'"main": self.main, "sub1": self.sub1, "sub2": self.sub2, "sub3": self.sub3, "sub4": self.sub4'
class WxButton(wx.Frame):

    def __init__(self, *args, **kw):
        global Relics
        super(WxButton, self).__init__(*args, **kw)
        self.mainstat = None
        self.substat1 = None
        self.substat2 = None
        self.substat3 = None
        self.substat4 = None
        self.InitUI()
    def __str__(self):
        return 'Relic Mainstat:'+ self.mainstat + 'Substats: ' + self.substat1 + ", " + self.substat2   + ", " + self.substat3 + ", " + self.substat4 + ", "


    def InitUI(self):
        pnl = wx.Panel(self)
        self.mainstat = wx.TextCtrl(pnl, style=wx.TE_MULTILINE, pos = (20,20))
        self.substat1 = wx.TextCtrl(pnl, style=wx.TE_MULTILINE, pos = (20,60))
        self.substat2 = wx.TextCtrl(pnl, style=wx.TE_MULTILINE, pos=(20, 100))
        self.substat3 = wx.TextCtrl(pnl, style=wx.TE_MULTILINE, pos=(160, 60))
        self.substat4 = wx.TextCtrl(pnl, style=wx.TE_MULTILINE, pos=(160, 100))
        relic = Relics(self.mainstat,self.substat1,self.substat2,self.substat3,self.substat4)
        self.stats = wx.StaticText(pnl, label=str(relic), pos=(20,160))

        closeButton = wx.Button(pnl, label='Close', pos=(20, 220))


        closeButton.Bind(wx.EVT_BUTTON, self.OnClose)

        self.SetSize((500, 300))
        self.SetTitle('Relic analysis')
        self.Centre()

    def OnClose(self, e):
        self.Close(True)

def main():
    app = wx.App()

    ex = WxButton(None)
    ex.Show()
    x = Relics(ex.mainstat, ex.substat1, ex.substat2, ex.substat3, ex.substat4)
    app.MainLoop()


main()





