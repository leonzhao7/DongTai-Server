

class GlobalDataSingleton:
    _instance = None
    _data = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_data(self):
        from dongtai_common.models.user import User

        if self._data is None:
            try:
                print(f"load global data ...")
                admin = User.objects.filter(username="admin").first()
                self._data = {"admin_id": admin.id}
                print(f"admin_id = {admin.id}")
            except Exception as e:
                print(f"加载全局数据失败: {str(e)}")
                self._data = {}

    @property
    def data(self):
        if self._data is None:
            self.load_data()
        return self._data

global_data = GlobalDataSingleton()
