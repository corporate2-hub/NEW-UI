from django import forms
from django.utils.safestring import mark_safe


class FontAwesomeIconPickerWidget(forms.TextInput):
    """
    Reusable Django Admin Font Awesome picker.

    Loads all Font Awesome FREE icons from CDN metadata.
    Stores values like:
        fa-solid fa-book
        fa-regular fa-user
        fa-brands fa-facebook
    """

    class Media:
        css = {
            "all": (
                "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.5.1/css/all.min.css",
            )
        }

    def render(self, name, value, attrs=None, renderer=None):
        value = value or ""
        attrs = attrs or {}

        input_id = attrs.get("id", f"id_{name}")
        wrapper_id = f"fa_picker_{input_id}"

        html = f"""
        <div id="{wrapper_id}" class="fa-picker-wrapper">
            <input type="hidden"
                   name="{name}"
                   id="{input_id}"
                   value="{value}">

            <div class="fa-picker-preview">
                <div class="fa-picker-current-icon">
                    {"<i class='" + value + "'></i><span>" + value + "</span>" if value else "<span>No icon selected</span>"}
                </div>

                <button type="button" class="fa-picker-clear">
                    Clear
                </button>
            </div>

            <input type="text"
                   class="fa-picker-search"
                   placeholder="Search Font Awesome icon...">

            <div class="fa-picker-status">
                Loading icons...
            </div>

            <div class="fa-picker-grid"></div>
        </div>

        <style>
            #{wrapper_id} {{
                margin-top: 8px;
                max-width: 100%;
            }}

            #{wrapper_id} .fa-picker-preview {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                padding: 10px 12px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                background: #ffffff;
                margin-bottom: 10px;
            }}

            #{wrapper_id} .fa-picker-current-icon {{
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 14px;
                color: #374151;
            }}

            #{wrapper_id} .fa-picker-current-icon i {{
                font-size: 24px;
                color: #2563eb;
            }}

            #{wrapper_id} .fa-picker-clear {{
                border: 1px solid #d1d5db;
                background: #f9fafb;
                color: #374151;
                padding: 5px 10px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
            }}

            #{wrapper_id} .fa-picker-clear:hover {{
                background: #f3f4f6;
            }}

            #{wrapper_id} .fa-picker-search {{
                width: 100%;
                padding: 9px 12px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                margin-bottom: 10px;
                font-size: 14px;
                box-sizing: border-box;
            }}

            #{wrapper_id} .fa-picker-status {{
                font-size: 13px;
                color: #6b7280;
                margin-bottom: 8px;
            }}

            #{wrapper_id} .fa-picker-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(145px, 1fr));
                gap: 8px;
                max-height: 420px;
                overflow-y: auto;
                padding: 8px;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                background: #f9fafb;
            }}

            #{wrapper_id} .fa-picker-option {{
                display: flex;
                align-items: center;
                gap: 8px;
                border: 1px solid #e5e7eb;
                background: #ffffff;
                padding: 8px 10px;
                border-radius: 8px;
                cursor: pointer;
                text-align: left;
                font-size: 13px;
                color: #374151;
                transition: all 0.15s ease;
            }}

            #{wrapper_id} .fa-picker-option i {{
                font-size: 18px;
                width: 24px;
                text-align: center;
                color: #4b5563;
            }}

            #{wrapper_id} .fa-picker-option:hover {{
                border-color: #2563eb;
                background: #eff6ff;
            }}

            #{wrapper_id} .fa-picker-option.selected {{
                border-color: #2563eb;
                background: #dbeafe;
                color: #1d4ed8;
            }}

            #{wrapper_id} .fa-picker-option.selected i {{
                color: #1d4ed8;
            }}

            #{wrapper_id} .fa-picker-option span {{
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
        </style>

        <script>
            (function() {{
                const wrapper = document.getElementById("{wrapper_id}");
                if (!wrapper) return;

                const input = wrapper.querySelector("#{input_id}");
                const preview = wrapper.querySelector(".fa-picker-current-icon");
                const search = wrapper.querySelector(".fa-picker-search");
                const clearBtn = wrapper.querySelector(".fa-picker-clear");
                const grid = wrapper.querySelector(".fa-picker-grid");
                const status = wrapper.querySelector(".fa-picker-status");

                const currentValue = "{value}";
                let allIcons = [];

                const metadataUrl = "https://cdn.jsdelivr.net/gh/FortAwesome/Font-Awesome@6.x/metadata/icons.json";


                function humanName(iconName) {{
                    return iconName.replace(/-/g, " ").replace(/\\b\\w/g, function(c) {{
                        return c.toUpperCase();
                    }});
                }}

                function styleToClass(style) {{
                    if (style === "solid") return "fa-solid";
                    if (style === "regular") return "fa-regular";
                    if (style === "brands") return "fa-brands";
                    return "fa-solid";
                }}

                function setIcon(iconClass) {{
                    input.value = iconClass;

                    wrapper.querySelectorAll(".fa-picker-option").forEach(function(option) {{
                        option.classList.toggle("selected", option.dataset.icon === iconClass);
                    }});

                    if (iconClass) {{
                        preview.innerHTML = '<i class="' + iconClass + '"></i><span>' + iconClass + '</span>';
                    }} else {{
                        preview.innerHTML = "<span>No icon selected</span>";
                    }}
                }}

                function renderIcons(icons) {{
                    grid.innerHTML = "";

                    const fragment = document.createDocumentFragment();

                    icons.forEach(function(item) {{
                        const button = document.createElement("button");
                        button.type = "button";
                        button.className = "fa-picker-option";
                        button.dataset.icon = item.className;
                        button.dataset.search = item.searchText;

                        if (item.className === currentValue) {{
                            button.classList.add("selected");
                        }}

                        button.innerHTML =
                            '<i class="' + item.className + '"></i>' +
                            '<span>' + item.label + '</span>';

                        button.addEventListener("click", function() {{
                            setIcon(item.className);
                        }});

                        fragment.appendChild(button);
                    }});

                    grid.appendChild(fragment);

                    status.textContent = icons.length + " icons loaded";
                }}

                function filterIcons() {{
                    const keyword = search.value.toLowerCase().trim();

                    if (!keyword) {{
                        renderIcons(allIcons.slice(0, 300));
                        status.textContent = "Showing first 300 icons. Search to find more from " + allIcons.length + " icons.";
                        return;
                    }}

                    const filtered = allIcons.filter(function(item) {{
                        return item.searchText.includes(keyword);
                    }}).slice(0, 500);

                    renderIcons(filtered);
                    status.textContent = filtered.length + " matching icons";
                }}

                fetch(metadataUrl)
                    .then(function(response) {{
                        if (!response.ok) {{
                            throw new Error("Unable to load Font Awesome metadata");
                        }}
                        return response.json();
                    }})
                    .then(function(data) {{
                        Object.keys(data).forEach(function(iconName) {{
                            const icon = data[iconName];
                            const freeStyles = icon.free || [];

                            freeStyles.forEach(function(style) {{
                                const prefix = styleToClass(style);
                                const className = prefix + " fa-" + iconName;
                                const label = humanName(iconName);

                                const terms = [
                                    iconName,
                                    label,
                                    className,
                                    style
                                ];

                                if (icon.label) terms.push(icon.label);
                                if (icon.search && icon.search.terms) {{
                                    terms.push(icon.search.terms.join(" "));
                                }}

                                allIcons.push({{
                                    name: iconName,
                                    style: style,
                                    className: className,
                                    label: label,
                                    searchText: terms.join(" ").toLowerCase()
                                }});
                            }});
                        }});

                        allIcons.sort(function(a, b) {{
                            return a.label.localeCompare(b.label);
                        }});

                        filterIcons();
                    }})
                    .catch(function(error) {{
                        status.textContent = "Could not load Font Awesome icons.";
                        console.error(error);
                    }});

                search.addEventListener("input", filterIcons);

                clearBtn.addEventListener("click", function() {{
                    setIcon("");
                }});
            }})();
        </script>
        """

        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        return data.get(name, "")