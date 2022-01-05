import copy
import functools
import random
import re

from collections import OrderedDict
from random import Random
from typing import Any, Callable, Dict, Hashable, List, Optional, Pattern, Sequence, Tuple, Union

from .config import DEFAULT_LOCALE
from .exceptions import UniquenessException
from .factory import Factory
from .generator import Generator
from .utils.distribution import choices_distribution

_UNIQUE_ATTEMPTS = 1000

class Faker:
    # eli::注意!!!Faker没有继承object主类,一个类的多有必须方法都会在这里实现.[可以查看 object 源码.]
    """Proxy class capable of supporting multiple locales"""
    # eli::代理类,支持多个地区(语言环境)
    cache_pattern: Pattern = re.compile(r"^_cached_\w*_mapping$")
    # eli::cache_pattern,类型是Pattern,compile返回的类型[Compile a regular expression pattern, returning a Pattern object.]
    generator_attrs = [
        attr for attr in dir(Generator) if not attr.startswith("__") and attr not in ["seed", "seed_instance", "random"]
    ]
    # eli::generator_attrs = [_Generator__config,_Generator__format_token,add_provider,del_arguments,format,
    # get_arguments,get_formatter,get_providers,parse,provider,set_arguments,set_formatter]

    def __init__(
        self,
        locale: Optional[Union[str, Sequence[str], Dict[str, Union[int, float]]]] = None,
        # eli:: local 默认类型为 Union[str,Sequence_str,Dict_str__int_OR_float] 或 None,并且赋值为None
        providers: Optional[List[str]] = None,
        # eli::默认类型List_str 或 None
        generator: Optional[Generator] = None,
        # eli::默认类型Generator 或 None
        includes: Optional[List[str]] = None,
        # eli::默认类型List_str 或 None
        use_weighting: bool = True,
        # eli::数据类型是布尔值
        **config: Any, # eli::config可以是任意数据类型,此处: Any 写不写一样.(python默认支持就是Any类型)
    ) -> None:
        # eli:: 返回类型默认是None
        self._factory_map = OrderedDict()
        self._weights = None
        self._unique_proxy = UniqueProxy(self)

        if isinstance(locale, str):
            locales = [locale.replace("-", "_")]

        # This guarantees a FIFO ordering of elements in `locales` based on the final
        # locale string while discarding duplicates after processing
        elif isinstance(locale, (list, tuple, set)):
            locales = []
            for code in locale:
                if not isinstance(code, str):
                    raise TypeError('The locale "%s" must be a string.' % str(code))
                final_locale = code.replace("-", "_")
                if final_locale not in locales:
                    locales.append(final_locale)

        elif isinstance(locale, OrderedDict):
            assert all(isinstance(v, (int, float)) for v in locale.values())
            odict = OrderedDict()
            for k, v in locale.items():
                key = k.replace("-", "_")
                odict[key] = v
            locales = list(odict.keys())
            self._weights = list(odict.values())

        else:
            locales = [DEFAULT_LOCALE] # eli::设置地区(语言) DEFAULT_LOCALE = "en_US"

        for locale in locales:
            # eli::self._factory_map = OrderedDict(),加载传递进来的所有参数,创建工厂类,存储在_factory_map:OrderedDict中.
            # eli:: 返回值:Factory.create->Generator is [faker]
            self._factory_map[locale] = Factory.create(
                locale,
                providers,
                generator,
                includes,
                use_weighting=use_weighting,
                **config,
            )

        self._locales = locales
        self._factories = list(self._factory_map.values())

    def __dir__(self):
        """
        eli::
        dir() 函数不带参数时，返回当前范围(模块)内的变量、方法和定义的类型列表；带参数时，返回参数的属性、方法列表。
        如果参数包含方法__dir__()，该方法将被调用。如果参数不包含__dir__()，该方法将最大限度地收集参数信息。
        """
        attributes = set(super(Faker, self).__dir__())  # eli:: 猜测这个是给继承Faker的子类使用的.
        for factory in self.factories:
            attributes |= {attr for attr in dir(factory) if not attr.startswith("_")}
            # eli::取并集 a | b  # 集合a或b中包含的所有元素

        """
        eli::fake = Faker();  print(dir(fake))
        ['__annotations__', '__class__', '__deepcopy__', '__delattr__', '__dict__', '__dir__', '__doc__', 
        '__eq__', '__format__', '__ge__', '__getattr__', '__getattribute__', '__getitem__', '__gt__', 
        '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', 
        '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__setstate__', '__sizeof__', 
        '__str__', '__subclasshook__', '__weakref__', '_factories', '_factory_map', '_locales', 
        '_map_provider_method', '_select_factory', '_unique_proxy', '_weights', 'aba', 'add_provider', 
        'address', 'administrative_unit', 'am_pm', 'android_platform_token', 'ascii_company_email', 
        'ascii_email', 'ascii_free_email', 'ascii_safe_email', 'bank_country', 'bban', 'binary', 'boolean', 
        'bothify', 'bs', 'building_number', 'cache_pattern', 'catch_phrase', 'century', 'chrome', 'city', 
        'city_prefix', 'city_suffix', 'color', 'color_name', 'company', 'company_email', 'company_suffix', 
        'coordinate', 'country', 'country_calling_code', 'country_code', 'credit_card_expire', 'credit_card_full', 
        'credit_card_number', 'credit_card_provider', 'credit_card_security_code', 'cryptocurrency', 
        'cryptocurrency_code', 'cryptocurrency_name', 'csv', 'currency', 'currency_code', 'currency_name', 
        'currency_symbol', 'current_country', 'current_country_code', 'date', 'date_between', 'date_between_dates', 
        'date_object', 'date_of_birth', 'date_this_century', 'date_this_decade', 'date_this_month', 'date_this_year', 
        'date_time', 'date_time_ad', 'date_time_between', 'date_time_between_dates', 'date_time_this_century', 
        'date_time_this_decade', 'date_time_this_month', 'date_time_this_year', 'day_of_month', 'day_of_week', 
        'del_arguments', 'dga', 'domain_name', 'domain_word', 'dsv', 'ean', 'ean13', 'ean8', 'ein', 'email', 
        'factories', 'file_extension', 'file_name', 'file_path', 'firefox', 'first_name', 'first_name_female', 
        'first_name_male', 'first_name_nonbinary', 'fixed_width', 'format', 'free_email', 'free_email_domain', 
        'future_date', 'future_datetime', 'generator_attrs', 'get_arguments', 'get_formatter', 'get_providers', 
        'hex_color', 'hexify', 'hostname', 'http_method', 'iana_id', 'iban', 'image', 'image_url', 'internet_explorer', 
        'invalid_ssn', 'ios_platform_token', 'ipv4', 'ipv4_network_class', 'ipv4_private', 'ipv4_public', 'ipv6', 
        'isbn10', 'isbn13', 'iso8601', 'items', 'itin', 'job', 'json', 'language_code', 'language_name', 'last_name', 
        'last_name_female', 'last_name_male', 'last_name_nonbinary', 'latitude', 'latlng', 'lexify', 'license_plate', 
        'linux_platform_token', 'linux_processor', 'local_latlng', 'locale', 'locales', 'localized_ean', 
        'localized_ean13', 'localized_ean8', 'location_on_land', 'longitude', 'mac_address', 'mac_platform_token', 
        'mac_processor', 'md5', 'military_apo', 'military_dpo', 'military_ship', 'military_state', 'mime_type', 
        'month', 'month_name', 'msisdn', 'name', 'name_female', 'name_male', 'name_nonbinary', 'nic_handle', 
        'nic_handles', 'null_boolean', 'numerify', 'opera', 'paragraph', 'paragraphs', 'parse', 'password', 
        'past_date', 'past_datetime', 'phone_number', 'port_number', 'postalcode', 'postalcode_in_state', 
        'postalcode_plus4', 'postcode', 'postcode_in_state', 'prefix', 'prefix_female', 'prefix_male', 
        'prefix_nonbinary', 'pricetag', 'profile', 'provider', 'providers', 'psv', 'pybool', 'pydecimal', 'pydict', 
        'pyfloat', 'pyint', 'pyiterable', 'pylist', 'pyset', 'pystr', 'pystr_format', 'pystruct', 'pytimezone', 
        'pytuple', 'random', 'random_choices', 'random_digit', 'random_digit_not_null', 
        'random_digit_not_null_or_empty', 'random_digit_or_empty', 'random_element', 'random_elements', 'random_int', 
        'random_letter', 'random_letters', 'random_lowercase_letter', 'random_number', 'random_sample', 
        'random_uppercase_letter', 'randomize_nb_elements', 'rgb_color', 'rgb_css_color', 'ripe_id', 'safari', 
        'safe_color_name', 'safe_domain_name', 'safe_email', 'safe_hex_color', 'secondary_address', 'seed', 
        'seed_instance', 'seed_locale', 'sentence', 'sentences', 'set_arguments', 'set_formatter', 'sha1', 'sha256', 
        'simple_profile', 'slug', 'ssn', 'state', 'state_abbr', 'street_address', 'street_name', 'street_suffix', 
        'suffix', 'suffix_female', 'suffix_male', 'suffix_nonbinary', 'swift', 'swift11', 'swift8', 'tar', 'text', 
        'texts', 'time', 'time_delta', 'time_object', 'time_series', 'timezone', 'tld', 'tsv', 'unique', 
        'unix_device', 'unix_partition', 'unix_time', 'upc_a', 'upc_e', 'uri', 'uri_extension', 'uri_page', 
        'uri_path', 'url', 'user_agent', 'user_name', 'uuid4', 'weights', 'windows_platform_token', 'word', 'words', 
        'year', 'zip', 'zipcode', 'zipcode_in_state', 'zipcode_plus4']
        """
        return sorted(attributes)

    def __getitem__(self, locale: str) -> Generator:
        """
        eli::当实例对象通过[] 运算符取值时，会调用它的方法__getitem__
        如果在类中定义了__getitem__()方法，那么他的实例对象（假设为P）就可以这样P[key]取值。
        当实例对象做P[key]运算时，就会调用类中的__getitem__()方法。
        """
        return self._factory_map[locale.replace("-", "_")]

    def __getattribute__(self, attr: str) -> Any:
        """
        Handles the "attribute resolution" behavior for declared members of this proxy class

        The class method `seed` cannot be called from an instance.

        :param attr: attribute name
        :return: the appropriate attribute
        """
        """
        eli::
        __getattribute__仅在新式类中可用，重载__getattrbute__方法对类实例的每个属性访问都有效，
        无论属性存不存在,访问类的属性时(P.attr)都会先调用__getattribute__方法
        """
        if attr == "seed":
            msg = "Calling `.seed()` on instances is deprecated. " "Use the class method `Faker.seed()` instead."
            raise TypeError(msg)
        else:
            # print("eli::Do->__getattribute__()",attr)
            """
            eli::[out]  fake = Faker();fake.name()
            eli::Do->__getattribute__() _factory_map
            eli::Do->__getattribute__() _factory_map
            eli::Do->__getattribute__() name
            eli::Do->__getattribute__() _factories
            eli::Do->__getattribute__() _factories
            """
            return super().__getattribute__(attr)

    def __getattr__(self, attr: str) -> Any:
        """
        eli::
        重载__getattr__方法对类及其实例未定义的属性有效。
        如果访问的属性存在，就不会调用__getattr__方法。这个属性的存在，包括类属性和实例属性
        """
        """
        Handles cache access and proxying behavior

        :param attr: attribute name
        :return: the appropriate attribute
        """
        if len(self._factories) == 1:
            # print("eli::__getattr__len(self._factories) == 1")
            # print(self._factories[0], attr)
            """
            eli::[out]
            eli::__getattr__len(self._factories) == 1
            <faker.generator.Generator object at 0x00000176F85CA280> name
            """
            # eli:: getattr() 函数用于返回一个对象属性值。
            # eli:: getattr(x, 'y') is equivalent to x.y,所以此处返回的是:Generator.name
            return getattr(self._factories[0], attr)
        elif attr in self.generator_attrs:
            msg = "Proxying calls to `%s` is not implemented in multiple locale mode." % attr
            raise NotImplementedError(msg)
        elif self.cache_pattern.match(attr):
            msg = "Cached attribute `%s` does not exist" % attr
            raise AttributeError(msg)
        else:
            factory = self._select_factory(attr)
            return getattr(factory, attr)

    def __deepcopy__(self, memodict: Dict = {}) -> "Faker":
        """
        eli::在调用deepcopy函数深拷贝对象时,首选调用对象的__deepcopy__函数
        """
        # print("eli::Do->__deepcopy__()",memodict)
        """
        eli::[out]fake2 = copy.deepcopy(fake)
        eli::Do->__deepcopy__() {}
        """
        cls = self.__class__
        result = cls.__new__(cls)
        result._locales = copy.deepcopy(self._locales)
        result._factories = copy.deepcopy(self._factories)
        result._factory_map = copy.deepcopy(self._factory_map)
        result._weights = copy.deepcopy(self._weights)
        result._unique_proxy = UniqueProxy(self)
        result._unique_proxy._seen = {k: {result._unique_proxy._sentinel} for k in self._unique_proxy._seen.keys()}
        return result

    def __setstate__(self, state: Any) -> None:
        """
        eli::
        __getstate__ 与 __setstate__ 两个魔法方法分别用于Python 对象的序列化与反序列化
        在序列化时, _getstate__ 可以指定将哪些信息记录下来, 而 __setstate__ 指明如何利用已记录的信息
        """
        self.__dict__.update(state)

    @property
    def unique(self) -> "UniqueProxy":
        return self._unique_proxy

    def _select_factory(self, method_name: str) -> Factory:
        """
        Returns a random factory that supports the provider method

        :param method_name: Name of provider method
        :return: A factory that supports the provider method
        """

        factories, weights = self._map_provider_method(method_name)
        if len(factories) == 0:
            msg = f"No generator object has attribute {method_name!r}"
            raise AttributeError(msg)
        elif len(factories) == 1:
            return factories[0]

        if weights:
            factory = choices_distribution(factories, weights, length=1)[0]
        else:
            factory = random.choice(factories)
        return factory

    def _map_provider_method(self, method_name: str) -> Tuple[List[Factory], Optional[List[float]]]:
        """
        Creates a 2-tuple of factories and weights for the given provider method name

        The first element of the tuple contains a list of compatible factories.
        The second element of the tuple contains a list of distribution weights.

        :param method_name: Name of provider method
        :return: 2-tuple (factories, weights)
        """

        # Return cached mapping if it exists for given method
        attr = f"_cached_{method_name}_mapping"
        if hasattr(self, attr):
            return getattr(self, attr)

        # Create mapping if it does not exist
        if self._weights:
            value = [
                (factory, weight)
                for factory, weight in zip(self.factories, self._weights)
                if hasattr(factory, method_name)
            ]
            factories, weights = zip(*value)
            mapping = list(factories), list(weights)
        else:
            value = [factory for factory in self.factories if hasattr(factory, method_name)]  # type: ignore
            mapping = value, None  # type: ignore

        # Then cache and return results
        setattr(self, attr, mapping)
        return mapping

    @classmethod
    def seed(cls, seed: Optional[Hashable] = None) -> None:
        """
        Hashables the shared `random.Random` object across all factories

        :param seed: seed value
        """
        Generator.seed(seed)

    def seed_instance(self, seed: Optional[Hashable] = None) -> None:
        """
        Creates and seeds a new `random.Random` object for each factory

        :param seed: seed value
        """
        for factory in self._factories:
            factory.seed_instance(seed)

    def seed_locale(self, locale: str, seed: Optional[Hashable] = None) -> None:
        """
        Creates and seeds a new `random.Random` object for the factory of the specified locale

        :param locale: locale string
        :param seed: seed value
        """
        self._factory_map[locale.replace("-", "_")].seed_instance(seed)

    @property
    def random(self) -> Random:
        """
        Proxies `random` getter calls

        In single locale mode, this will be proxied to the `random` getter
        of the only internal `Generator` object. Subclasses will have to
        implement desired behavior in multiple locale mode.
        """

        if len(self._factories) == 1:
            return self._factories[0].random
        else:
            msg = "Proxying `random` getter calls is not implemented in multiple locale mode."
            raise NotImplementedError(msg)

    @random.setter
    def random(self, value: Random) -> None:
        """
        Proxies `random` setter calls

        In single locale mode, this will be proxied to the `random` setter
        of the only internal `Generator` object. Subclasses will have to
        implement desired behavior in multiple locale mode.
        """

        if len(self._factories) == 1:
            self._factories[0].random = value
        else:
            msg = "Proxying `random` setter calls is not implemented in multiple locale mode."
            raise NotImplementedError(msg)

    @property
    def locales(self) -> List[str]:
        return list(self._locales)

    @property
    def weights(self) -> Optional[List[Union[int, float]]]:
        return self._weights

    @property
    def factories(self) -> List[Generator]:
        return self._factories

    def items(self) -> List[Tuple[str, Generator]]:
        return list(self._factory_map.items())


class UniqueProxy:
    def __init__(self, proxy: Faker):
        self._proxy = proxy
        self._seen: Dict = {}
        self._sentinel = object()

    def clear(self) -> None:
        self._seen = {}

    def __getattr__(self, name: str) -> Any:
        obj = getattr(self._proxy, name)
        if callable(obj):
            return self._wrap(name, obj)
        else:
            raise TypeError("Accessing non-functions through .unique is not supported.")

    def __getstate__(self):
        # Copy the object's state from self.__dict__ which contains
        # all our instance attributes. Always use the dict.copy()
        # method to avoid modifying the original state.
        state = self.__dict__.copy()
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def _wrap(self, name: str, function: Callable) -> Callable:
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            key = (name, args, tuple(sorted(kwargs.items())))

            generated = self._seen.setdefault(key, {self._sentinel})

            # With use of a sentinel value rather than None, we leave
            # None open as a valid return value.
            retval = self._sentinel

            for i in range(_UNIQUE_ATTEMPTS):
                if retval not in generated:
                    break
                retval = function(*args, **kwargs)
            else:
                raise UniquenessException(f"Got duplicated values after {_UNIQUE_ATTEMPTS:,} iterations.")

            generated.add(retval)

            return retval

        return wrapper
